import asyncio
from aiohttp import web


REQUEST_HEADER_BLACKLIST = [
    'Upgrade-Insecure-Requests'
]

RESPONSE_HEADER_BLACKLIST = [
    'Strict-Transport-Security'
]


def strip_request_headers(headers):
    for header in REQUEST_HEADER_BLACKLIST:
        try:
            headers.pop('Upgrade-Insecure-Requests', None)
        except KeyError:
            pass


async def strip(request):
    return web.Response(text="Hello world!")


async def main():
    server = web.Server(strip)
    await asyncio.get_running_loop().create_server(server, "127.0.0.1", 8080)
    print("======= Serving on http://127.0.0.1:8080/ ======")
    await asyncio.sleep(100 * 3600)
    print("hi")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
