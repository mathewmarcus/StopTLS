import asyncio
import aiohttp.web
import bs4
import urllib.parse
from resolver import dns_resolve


REQUEST_HEADER_BLACKLIST = [
    'Upgrade-Insecure-Requests'
]

RESPONSE_HEADER_BLACKLIST = [
    'Strict-Transport-Security'
]


url_tracker = {}


def strip_request_headers(headers):
    headers = dict(headers)
    for header in REQUEST_HEADER_BLACKLIST:
        headers.pop(header, None)

    return headers



class Handler(object):
    def __init__(self):
        self._tcp_connector = aiohttp.TCPConnector(ttl_dns_cache=None)
        # self.session = aiohttp.ClientSession(connector=self._tcp_connector)
        self.session = aiohttp.ClientSession(self._tcp_connector)
        self.stripped_urls = {}

    async def strip(self, request):
        request['remote_socket'] = '{}:{}'.format(*request.transport.get_extra_info('peername'))
        response = await self.proxy_request(request)
        return response

    async def proxy_request(self, request):
        orig_headers = dict(request.headers)
        headers = strip_request_headers(orig_headers)

        try:
            if (request.host + request.rel_url.human_repr()) in self.stripped_urls[request['remote_ip']]:
                scheme = 'https'
        except KeyError:
            scheme = request.scheme
        else:
            scheme = request.scheme

        url = urllib.parse.urlunsplit((scheme,
                                       request.host,
                                       request.path,
                                       request.query_string,
                                       request.url.fragment))

        method = request.method.lower()

        data = request.content if request.body_exists else None

        async with self.session.request(method,
                                        url,
                                        data=data,
                                        headers=headers,
                                        allow_redirects=False) as response:
            return response

    async def strip_response(response):
        # strip urls from headers

        # strip urls from HTML and Javascript bodies

        # remove SECURE flag from cookies
        pass

    async def kill_sessions(request):
        # remove existing cookies
        # potentiall remove Authorization: Bearer entries
        pass


async def web_main():
    # HTTP is a special case because it uses aiohttp
    # rather than raw asyncio. As such, it differs in two ways
    #    1. It has a seperate, individual port/handler
    #    2. It uses loop.start_server instead of create_server,
    #       in order to adhere to the aiohttp documentation

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
    servers = asyncio.gather(web_main(), generic_tcp_main())
    # loop.run_until_complete(asyncio.wait([asyncio.ensure_future(web_main()), asyncio.ensure_future(generic_tcp_main())], return_when=asyncio.FIRST_EXCEPTION))
    loop.run_until_complete(servers)
