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
    print('hi')
    return web.Response(text="Hello world!")


async def web_main():
    # HTTP is a special case because it uses aiohttp
    # rather than raw asyncio. As such, it differs in two ways
    #    1. It has a seperate, individual port/handler
    #    2. It uses loop.start_server instead of create_server,
    #       in order to mimic the aiohttp documentation
    server = await asyncio.get_running_loop().create_server(web.Server(strip),
                                                            None,
                                                            8080)
    print("======= Serving HTTP on 127.0.0.1:8080 ======")

    async with server:
        await server.serve_forever()


async def generic_tcp_main():
    server = await asyncio.start_server(lambda x: 1, '127.0.0.1', 8081)

    print("======= Serving generic TCP on 127.0.0.1:8081 ======")

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    servers = asyncio.shield(asyncio.gather(web_main(), generic_tcp_main()))
    loop.run_until_complete(servers)
