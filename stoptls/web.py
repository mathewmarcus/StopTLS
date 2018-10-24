import asyncio
import aiohttp.web
import urllib.parse
from resolver import dns_resolve


REQUEST_HEADER_BLACKLIST = [
    'Upgrade-Insecure-Requests'
]

RESPONSE_HEADER_BLACKLIST = [
    'Strict-Transport-Security'
]


def strip_request_headers(headers):
    headers = dict(headers)
    for header in REQUEST_HEADER_BLACKLIST:
        headers.pop(header, None)

    return headers


async def proxy_request(request, session):
        orig_headers = dict(request.headers)
        headers = strip_request_headers(orig_headers)

        host = await dns_resolve(request.host)

        scheme, netloc, path, params, query, frag = urllib.parse.urlparse(request.url)
        url = urllib.parse.urlunparse(request.scheme, host, request.path, params, request.query_string, frag)

        method = request.method.lower()

        data = request.content if request.body_exists else None

        async with session.request(method, url, data=data, headers=headers) as response:
            return response


class Handler(object):
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def strip(self, request):
        response = await proxy_request(request, self.session)
        return response


# async def strip(request):
#     orig_headers = dict(request.headers)
#     headers = strip_request_headers(orig_headers)

#     sock = await dns_resolve(headers['Host'])

#     return asyncio.web.Response(text=sock)


async def web_main():
    # HTTP is a special case because it uses aiohttp
    # rather than raw asyncio. As such, it differs in two ways
    #    1. It has a seperate, individual port/handler
    #    2. It uses loop.start_server instead of create_server,
    #       in order to mimic the aiohttp documentation

    handler = Handler()

    server = await asyncio.get_running_loop().create_server(aiohttp.web.Server(handler.strip),
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
    # servers = asyncio.gather(web_main(), generic_tcp_main())
    loop.run_until_complete(asyncio.wait([asyncio.ensure_future(web_main()), asyncio.ensure_future(generic_tcp_main())]))
    # loop.run_until_complete(servers)
