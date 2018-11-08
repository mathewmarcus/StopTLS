import urllib.parse

from stoptls.web import regex


class RequestProxy(object):
    HEADER_BLACKLIST = [
        'Upgrade-Insecure-Requests',
        'Host'
    ]

    def __init__(self, request):
        self.request = request
        self.client_ip = request.remote
        self.host = request.host
        self.cache = request['cache']
        self.session = request['session']

    async def proxy_request(self):
        # check if URL was previously stripped and cached
        if self.cache.has_url(self.client_ip,
                              self.host,
                              self.request.rel_url.human_repr()):
            scheme = 'https'
        else:
            scheme = 'http'

        headers = self.filter_and_strip_headers(dict(self.request.headers))

        # Kill sesssions
        cookies = self.filter_cookies(self.request.cookies)
        headers['Cookie'] = '; '.join(cookies)
        # TODO: possibly also remove certain types of auth (e.g. Authentication: Bearer)

        url = urllib.parse.urlunsplit((scheme,
                                       self.host,
                                       self.request.path,
                                       '',
                                       self.request.url.fragment))

        #TODO: possibly use built-in aiohttp.ClientSession cache to store cookies,
        # maybe by subclassing aiohttp.abc.AbstractCookieJar
        return await self.session.request(self.request.method.lower(),
                                          url,
                                          data=self.request.content if self.request.can_read_body else None,
                                          headers=headers,
                                          params=self.unstrip_query_params(self.request.url.query),
                                          allow_redirects=False)

    def filter_and_strip_headers(self, headers):
        for header in type(self).HEADER_BLACKLIST:
            headers.pop(header, None)

        try:
            parsed_origin = urllib.parse.urlsplit(headers['Origin'])
            if self.cache.has_domain(self.request.remote_ip, parsed_origin.netloc):
                headers['Origin'] = parsed_origin._replace(scheme='https').geturl()
        except KeyError:
            pass

            return headers

    def unstrip_query_params(self, query_params):
        unstripped_params = query_params.copy()
        for key, value in query_params.items():

            # unstrip secure URLs in path params
            if regex.UNSECURE_URL.fullmatch(value):
                parsed_url = urllib.parse.urlsplit(value)
                if self.cache.has_url(self.client_ip,
                                      parsed_url.netloc,
                                      urllib.parse.urlunsplit(('',
                                                               '',
                                                               parsed_url.path,
                                                               parsed_url.query,
                                                               parsed_url.fragment))):
                    unstripped_params.update({key: parsed_url._replace(scheme='https').geturl()})

    def filter_cookies(self, cookies):
        for name, value in cookies.items():
            if self.cache.has_cookie(self.client_ip,
                                     self.host,
                                     name):
                yield '{}={}'.format(name, value)
