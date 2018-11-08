import urllib.parse

from stoptls.web import regex


class RequestProxy(object):
    HEADER_BLACKLIST = [
        'Upgrade-Insecure-Requests',
        'Host'
    ]

    def __init__(self, request):
        self.request = request
        self.host = request.host
        self.cache = request['cache']
        self.session = request['session']

    async def proxy_request(self):
        # check if URL was previously stripped and cached
        if self.cache.has_url(self.host,
                              self.request.rel_url.human_repr()):
            scheme = 'https'
        else:
            scheme = 'http'

        query_params = self.unstrip_query_params(self.request.url.query)

        orig_headers = dict(self.request.headers)
        headers = self.filter_and_strip_headers(orig_headers)

        # Kill sesssions
        cookies = self.filter_cookies(self.request.cookies)
        headers['Cookie'] = '; '.join(cookies)
        # TODO: possibly also remove certain types of auth (e.g. Authentication: Bearer)

        url = urllib.parse.urlunsplit((scheme,
                                       self.host,
                                       self.request.path,
                                       '',
                                       self.request.url.fragment))
        method = self.request.method.lower()
        data = self.request.content if self.request.can_read_body else None

        #TODO: possibly use built-in aiohttp.ClientSession cache to store cookies,
        # maybe by subclassing aiohttp.abc.AbstractCookieJar
        return await self.session.request(method,
                                          url,
                                          data=data,
                                          headers=headers,
                                          params=query_params,
                                          # max_redirects=100)
                                          allow_redirects=False)  # potentially set this to False to prevent auto-redirection)

    def filter_and_strip_headers(self, headers):
        for header in type(self).HEADER_BLACKLIST:
            headers.pop(header, None)

        try:
            parsed_origin = urllib.parse.urlsplit(headers['Origin'])
            if self.cache.has_domain(parsed_origin.netloc):
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
                if self.cache.has_url(parsed_url.netloc,
                                      urllib.parse.urlunsplit(('',
                                                               '',
                                                               parsed_url.path,
                                                               parsed_url.query,
                                                               parsed_url.fragment))):
                    unstripped_params.update({key: parsed_url._replace(scheme='https').geturl()})
        return unstripped_params

    def filter_cookies(self, cookies):
        for name, value in cookies.items():
            if self.cache.has_cookie(self.host,
                                     name):
                yield '{}={}'.format(name, value)
