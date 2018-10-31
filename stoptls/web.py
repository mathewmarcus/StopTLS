import asyncio
import aiohttp.web
import bs4
import urllib.parse
import re

from stoptls.cache import InMemoryCache


HEADER_BLACKLIST = {
    'request': [
        'Upgrade-Insecure-Requests',
        'Host'
    ],
    'response': [
        'Strict-Transport-Security',
        'Content-Length',
        'Content-Encoding',
        'Transfer-Encoding',
        'Set-Cookie'
    ]
}

SCHEME_DELIMITER = re.compile(':\/\/|:(?:\\\\x2[Ff]){2}|%3[Aa](?:%2[Ff]){2}')
SCHEME = re.compile('(?:https)({})'.format(SCHEME_DELIMITER.pattern))
SECURE_URL = re.compile('(?:https)((?:{})[a-zA-z0-9.\/?\-#=&;%:~_$@+,\\\\]+)'
                        .format(SCHEME_DELIMITER.pattern),
                        flags=re.IGNORECASE)
COOKIE_SECURE_FLAG = re.compile('Secure;?',
                                flags=re.IGNORECASE)
CSS_OR_SCRIPT = re.compile('^script$|^style$')

url_tracker = {}


def strip_headers(headers, type_):
    for header in HEADER_BLACKLIST[type_]:
        headers.pop(header, None)

    return headers


class Handler(object):
    def __init__(self):
        self._tcp_connector = aiohttp.TCPConnector(ttl_dns_cache=None)
        self.session = aiohttp.ClientSession(connector=self._tcp_connector,
                                             cookie_jar=aiohttp.DummyCookieJar())
        self.cache = InMemoryCache()

    async def strip(self, request):
        response = await self.proxy_request(request)
        stripped_response = await self.strip_response(response, request.remote)
        await stripped_response.prepare(request)
        return stripped_response

    async def proxy_request(self, request):
        # check if URL was previously stripped and cached
        scheme = 'https' \
            if self.cache.has_url(request.remote,
                                  request.host,
                                  request.rel_url.human_repr()) \
            else 'http'

        orig_headers = dict(request.headers)
        headers = strip_headers(orig_headers, 'request')

        # Kill sesssions
        cookies = self.filter_incoming_cookies(request.cookies,
                                               request.remote,
                                               request.host)
        headers['Cookie'] = '; '.join(cookies)

        # TODO: possibly also remove certain types of auth (e.g. Authentication: Bearer)

        url = urllib.parse.urlunsplit((scheme,
                                       request.host,
                                       request.path,
                                       request.query_string,
                                       request.url.fragment))
        method = request.method.lower()
        data = request.content if request.can_read_body else None

        #TODO: possibly use built-in aiohttp.ClientSession cache to store cookies,
        # maybe by subclassing aiohttp.abc.AbstractCookieJar
        return await self.session.request(method,
                                          url,
                                          data=data,
                                          headers=headers,
                                          # max_redirects=100)
                                          allow_redirects=False)  # potentially set this to False to prevent auto-redirection)

    async def strip_response(self, response, remote_ip):
        # strip secure URLs from HTML and Javascript bodies
        if response.content_type == 'text/html':
            body = self.strip_html_body(await response.text(), remote_ip)
        elif response.content_type == 'application/javascript' or response.content_type == 'text/css':
            body = self.strip_text(await response.text(), remote_ip)
        else:
            body = await response.read()
            # response.release()

        headers = strip_headers(dict(response.headers), 'response')

        # strip secure URL from location header
        try:
            location = headers['Location']
            headers['Location'] = location.replace('https://', 'http://')
            self.cache.add_url(remote_ip, location)
        except KeyError:
            pass

        stripped_response = aiohttp.web.Response(body=body,
                                                 status=response.status,
                                                 headers=headers)

        # remove secure flag from cookies
        for cookie_name, cookie_directives in response.cookies.items():
            # cache newly-set cookies
            self.cache.add_cookie(remote_ip,
                                  response.url.host,
                                  cookie_name)

            # remove "secure" directive
            cookie_directives.pop('secure', None)

            # aiohttp.web.Response.set_cookie doesn't allow "comment" directive
            # as a kwarg
            cookie_directives.pop('comment', None)

            stripped_directives = {}
            for directive_name, directive_value in cookie_directives.items():
                if directive_value and cookie_directives.isReservedKey(directive_name):
                    stripped_directives[directive_name.replace('-', '_')] = directive_value

            stripped_response.set_cookie(cookie_name,
                                         cookie_directives.value,
                                         **stripped_directives)
        return stripped_response

    def strip_html_body(self, body, remote_ip):
        soup = bs4.BeautifulSoup(body, 'html.parser')
        secure_url_attrs = []

        def has_secure_url_attr(tag):
            found = False
            url_attrs = []
            for attr_name, attr_value in tag.attrs.items():
                if isinstance(attr_value, list):
                    attr_value = ' '.join(attr_value)

                if SECURE_URL.fullmatch(attr_value):
                    url_attrs.append(attr_name)
                    self.cache.add_url(remote_ip, attr_value)
                    found = True

            if url_attrs:
                secure_url_attrs.append(url_attrs)

            return found

        secure_tags = soup.find_all(has_secure_url_attr)

        for i, tag in enumerate(secure_tags):
            for attr in secure_url_attrs[i]:
                secure_url = tag[attr]
                tag[attr] = secure_url.replace('https://', 'http://')

        # strip secure URLs from <style> and <script> blocks
        css_or_script_tags = soup.find_all(CSS_OR_SCRIPT)
        for tag in css_or_script_tags:
            if tag.string:
                tag.string = self.strip_text(tag.string, remote_ip)

        return str(soup)

    def strip_text(self, body, remote_ip):
        def generate_unsecure_replacement(secure_url):
            self.cache.add_url(remote_ip, secure_url.group(0))
            return 'http' + secure_url.group(1)

        return SECURE_URL.sub(generate_unsecure_replacement, body)

    def filter_incoming_cookies(self, cookies, remote_ip, host):
        for name, value in cookies.items():
            if self.cache.has_cookie(remote_ip,
                                     host,
                                     name):
                yield '{}={}'.format(name, value)


async def main():
    # HTTP is a special case because it uses aiohttp
    # rather than raw asyncio. As such, it differs in two ways
    #    1. It has a seperate, individual port/handler
    #    2. It uses loop.create_server instead of start_server,
    #       in order to adhere to the aiohttp documentation

    handler = Handler()
    server = await asyncio.get_running_loop().create_server(aiohttp.web.Server(handler.strip),
                                                            None,
                                                            8080)
    print("======= Serving HTTP on 127.0.0.1:8080 ======")

    async with server:
        await server.serve_forever()
