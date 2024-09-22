import asyncio

async def tcp_echo_client():
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 10721)

    while True:
        data = await reader.read(100)
        if not data:
            break
        print(f'Received: {data}')

        writer.write(("给你一拳").encode())
        await writer.drain()

    print('Connection closed by the server')
    writer.close()
    await writer.wait_closed()

asyncio.run(tcp_echo_client())
