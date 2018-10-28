import asyncio


async def main():
    server = await asyncio.start_server(lambda x: 1, '127.0.0.1', 8081)

    print("======= Serving generic TCP on 127.0.0.1:8081 ======")

    async with server:
        await server.serve_forever()
