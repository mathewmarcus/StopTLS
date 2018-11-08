import aiohttp.web
import bs4
import urllib.parse

from stoptls.web import regex


class ResponseProxy(object):
    HEADER_BLACKLIST = [
        'Strict-Transport-Security',
        'Content-Length',
        'Content-Encoding',
        'Transfer-Encoding',
        'Set-Cookie'
    ]

    def __init__(self, response, host, cache):
        self.response = response
        self.host = host
        self.cache = cache

    async def strip_response(self):
        # strip secure URLs from HTML and Javascript bodies
        if self.response.content_type == 'text/html':
            try:
                body = await self.response.text()
            except UnicodeDecodeError:
                raw_body = await self.response.read()
                body = raw_body.decode('utf-8')
            body = self.strip_html_body(body)
        elif self.response.content_type == 'application/javascript':
            body = self.strip_text(await self.response.text())
        elif self.response.content_type == 'text/css':
            body = self.strip_text(await self.response.text())
        else:
            body = await self.response.read()
            # response.release()

        headers = self.filter_and_strip_headers(dict(self.response.headers))

        stripped_response = aiohttp.web.Response(body=body,
                                                 status=self.response.status,
                                                 headers=headers)

        # remove secure flag from cookies
        for name, value, directives in self.strip_cookies(self.response.cookies,
                                                          self.response.url.host):
            stripped_response.set_cookie(name, value, **directives)

        return stripped_response

    def strip_html_body(self, body):
        soup = bs4.BeautifulSoup(body, 'html.parser')
        secure_url_attrs = []

        def has_secure_url_attr(tag):
            found = False
            url_attrs = []
            for attr_name, attr_value in tag.attrs.items():
                if isinstance(attr_value, list):
                    attr_value = ' '.join(attr_value)

                if regex.SECURE_URL.fullmatch(attr_value):
                    url_attrs.append(attr_name)
                    self.cache.add_url(attr_value)
                    found = True
                elif regex.RELATIVE_URL.fullmatch(attr_value):
                    url_attrs.append(attr_name)
                    self.cache.add_url(attr_value, host=self.host)
                    found = True

            if url_attrs:
                secure_url_attrs.append(url_attrs)

            return found

        secure_tags = soup.find_all(has_secure_url_attr)

        for i, tag in enumerate(secure_tags):
            for attr in secure_url_attrs[i]:
                secure_url = tag[attr]
                if secure_url.startswith('/'):
                    tag[attr] = 'http://{}{}'.format(self.host, secure_url)
                else:
                    parsed_url = urllib.parse.urlsplit(secure_url)
                    tag[attr] = urllib.parse.urlunsplit(parsed_url._replace(scheme='http'))

        # strip secure URLs from <style> and <script> blocks
        css_or_script_tags = soup.find_all(regex.CSS_OR_SCRIPT)
        for tag in css_or_script_tags:
            if tag.string:
                tag.string = self.strip_text(tag.string)

        return str(soup)

    def strip_text(self, body):
        def generate_unsecure_replacement(secure_url):
            self.cache.add_url(secure_url.group(0))
            return 'http' + secure_url.group(1)

        def relative2absolute_url(relative_url):
            self.cache.add_url(relative_url.group(0), self.host)
            return 'http://{}{}'.format(self.host, relative_url)

        canonicalized_text = regex.RELATIVE_URL.sub(relative2absolute_url,
                                                    body)
        return regex.SECURE_URL.sub(generate_unsecure_replacement,
                                    canonicalized_text)

    def strip_cookies(self, cookies, host):
        for cookie_name, cookie_directives in cookies.items():
            # cache newly-set cookies
            self.cache.add_cookie(host,
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

            yield cookie_name, cookie_directives.value, stripped_directives

    def filter_and_strip_headers(self, headers):
        for header in type(self).HEADER_BLACKLIST:
            headers.pop(header, None)

        # strip secure URL from location header
        try:
            location = headers['Location']
            headers['Location'] = location.replace('https://', 'http://')
            self.cache.add_url(location)
        except KeyError:
            pass

        return headers
