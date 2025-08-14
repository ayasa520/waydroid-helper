import asyncio
import threading

from waydroid_helper.controller.core.control_msg import ControlMsg
from waydroid_helper.controller.core.event_bus import (Event, EventType,
                                                       event_bus)
from waydroid_helper.util.log import logger


class Server:
    """服务器类 - 严格单例模式"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, host: str = "0.0.0.0", port: int = 10721):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host: str = "0.0.0.0", port: int = 10721):
        # 防止重复初始化
        if Server._initialized:
            return

        with Server._lock:
            if Server._initialized:
                return

            self.host: str = host
            self.port: int = port
            self.message_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
            event_bus.subscribe(EventType.CONTROL_MSG, self.send_msg, subscriber=self)
            self.server: asyncio.Server | None = None
            self.writers: list[asyncio.StreamWriter] = []
            self.started_event = asyncio.Event()
            self.server_task: asyncio.Task[None] = asyncio.create_task(self.start_server())

            Server._initialized = True
            logger.info(f"Server singleton initialized on {host}:{port}")

    async def handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        logger.info(f"Connected to {addr!r}")
        info = await reader.read(64)
        logger.info(f"Connected to {info.decode()}")
        self.writers.append(writer)

        try:
            while True:
                message = await self.message_queue.get()
                if not message:
                    break
                writer.write(message)
                await writer.drain()
        finally:
            logger.info(f"Closing the connection to {addr!r}")
            self.writers.remove(writer)
            writer.close()
            await writer.wait_closed()

    async def start_server(self):
        try:
            self.server = await asyncio.start_server(self.handler, self.host, self.port)

            addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
            logger.info(f"Serving on {addrs}")
            self.started_event.set()

            async with self.server:
                await self.server.serve_forever()
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.started_event.set() # Set event on failure to avoid deadlocks

    async def wait_started(self):
        await self.started_event.wait()

    def close(self):
        if self.server:
            asyncio.create_task(self._close())

    async def _close(self):
        if not self.server:
            return

        self.server.close()
        await self.server.wait_closed()

        # Wake up handlers to exit
        await self.message_queue.put(None)

        # Close all client connections
        for writer in self.writers:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()

        if not self.server_task.done():
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        logger.info("Server closed.")

    def send(self, msg: bytes):
        asyncio.create_task(self.message_queue.put(msg))

    def send_msg(self, event: Event[ControlMsg]):
        msg: ControlMsg = event.data
        logger.debug("Send: %s", msg)
        packed_msg: bytes | None = msg.pack()
        if packed_msg is not None:
            self.send(packed_msg)

    @classmethod
    def reset_singleton(cls) -> None:
        """重置单例状态 - 主要用于测试和窗口重新打开"""
        with cls._lock:
            if cls._instance is not None:
                # 先关闭现有的服务器
                cls._instance.close()
            cls._instance = None
            cls._initialized = False
            logger.info("Server singleton reset")


# async def main():
#     server = Server('127.0.0.1', 10721)
#     await server.start_server()

# if __name__ == '__main__':
#     task = asyncio.run(main())
