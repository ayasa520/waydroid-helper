import asyncio
import logging
from waydroid_helper.controller.core.event_bus import EventType, event_bus, Event
from waydroid_helper.controller.core.control_msg import ControlMsg
from waydroid_helper.util.log import logger


class Server:
    def __init__(self, host: str, port: int):
        self.host: str = host
        self.port: int = port
        self.logger: logging.Logger = logger
        self.message_queue: asyncio.Queue[bytes] = asyncio.Queue()
        event_bus.subscribe(EventType.CONTROL_MSG, self.send_msg)
        asyncio.create_task(self.start_server())

    async def handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        self.logger.info(f"Connected to {addr!r}")

        while True:
            message = await self.message_queue.get()
            if not message:
                break
            writer.write(message)
            await writer.drain()

        self.logger.info("Closing the connection")
        writer.close()
        await writer.wait_closed()

    async def start_server(self):
        server = await asyncio.start_server(self.handler, self.host, self.port)

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        self.logger.info(f"Serving on {addrs}")

        async with server:
            await server.serve_forever()

    def send(self, msg: bytes):
        asyncio.create_task(self.message_queue.put(msg))

    def send_msg(self, event: Event[ControlMsg]):
        msg: ControlMsg = event.data
        self.logger.info(f"Send: {msg!r}")
        packed_msg: bytes | None = msg.pack()
        if packed_msg is not None:
            self.send(packed_msg)


# async def main():
#     server = Server('127.0.0.1', 10721)
#     await server.start_server()

# if __name__ == '__main__':
#     task = asyncio.run(main())
