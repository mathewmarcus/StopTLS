import asyncio

from stoptls.tcp.imap import IMAPProxy


async def main():
    server = await asyncio.start_server(IMAPProxy().strip, port=14314)

    print("======= Serving IMAP on 14314 ======")

    async with server:
        await server.serve_forever()
