import asyncio
import aiohttp.web

from stoptls.web.request import RequestProxy
from stoptls.web.response import ResponseProxy
from stoptls.cache import InMemoryCache


class WebProxy(object):
    def __init__(self):
        self._tcp_connector = aiohttp.TCPConnector(ttl_dns_cache=None)
        self.session = aiohttp.ClientSession(connector=self._tcp_connector,
                                             cookie_jar=aiohttp.DummyCookieJar())
        self.cache = InMemoryCache()

    async def strip(self, request):
        request['cache'] = self.cache.get_client_cache(request.remote)
        request['session'] = self.session
        response = await RequestProxy(request).proxy_request()
        stripped_response = await ResponseProxy(response,
                                                request.host,
                                                request['cache']).strip_response()
        await stripped_response.prepare(request)
        return stripped_response


async def main():
    # HTTP is a special case because it uses aiohttp
    # rather than raw asyncio. As such, it differs in two ways
    #    1. It has a seperate, individual port/handler
    #    2. It uses loop.create_server instead of start_server,
    #       in order to adhere to the aiohttp documentation

    server = await asyncio\
        .get_running_loop()\
        .create_server(aiohttp.web.Server(WebProxy().strip),
                       port=8080)
    print("======= Serving HTTP on 8080 ======")

    async with server:
        await server.serve_forever()
