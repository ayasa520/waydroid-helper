import asyncio

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.message_queue = asyncio.Queue()
        asyncio.create_task(self.start_server())

    async def handler(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Connected to {addr!r}")

        while True:
            message = await self.message_queue.get()
            if message is None:
                break
            # print(f"Send: {message!r}")
            writer.write(message)
            await writer.drain()
            # print(f"Sent {message!r} to {addr!r}")

        print("Closing the connection")
        writer.close()
        await writer.wait_closed()

    async def start_server(self):
        server = await asyncio.start_server(
            self.handler, self.host, self.port)

        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        print(f'Serving on {addrs}')

        async with server:
            await server.serve_forever()

    def send(self, msg:bytes):
        asyncio.create_task(self.message_queue.put(msg))

# async def main():
#     server = Server('127.0.0.1', 10721)
#     await server.start_server()

# if __name__ == '__main__':
#     task = asyncio.run(main())