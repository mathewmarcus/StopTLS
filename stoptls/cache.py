from abc import ABC, abstractmethod
import urllib.parse


class Cache(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def add_url(self, remote_socket, url):
        pass

    @abstractmethod
    def has_url(self, remote_socket, url):
        pass

    @abstractmethod
    def add_cookie(self, remote_socket, cookie):
        pass

    @abstractmethod
    def has_cookie(self, remote_socket, cookie):
        pass


class InMemoryCache(Cache):
    def __init__(self):
        self.cache = {}

    def add_url(self, remote_socket, url, host=None):
        # unescape URL
        try:
            unescaped_url = bytes(url, 'ascii').decode('unicode_escape')
        except UnicodeDecodeError:
            unescaped_url = url

        unquoted_url = urllib.parse.unquote_plus(unescaped_url)
        scheme, netloc, path, query, frag = urllib.parse.urlsplit(unquoted_url)

        if netloc or not host:
            host = netloc

        rel_url = urllib.parse.urlunsplit(('', '', path, query, frag))
        self.cache.setdefault(remote_socket, {})\
                  .setdefault(host, {})\
                  .setdefault('rel_urls', set([]))\
                  .add(rel_url)

    def has_url(self, remote_socket, host, rel_url):
        try:
            return urllib.parse.unquote_plus(rel_url) in self.cache[remote_socket][host]['rel_urls']
        except KeyError:
            return False
        else:
            return False

    def add_cookie(self, remote_socket, host, cookie):
        self.cache.setdefault(remote_socket, {})\
                  .setdefault(host, {})\
                  .setdefault('cookies', set([]))\
                  .add(cookie)

    def has_cookie(self, remote_socket, host, cookie):
        try:
            return cookie in self.cache[remote_socket][host]['cookies']
        except KeyError:
            return False
        else:
            return False

    def has_domain(self, remote_socket, host):
        try:
            return self.cache[remote_socket][host]
        except KeyError:
            return False

    def get_client_cache(self, client_ip):
        return ClientCache(self.cache.setdefault(client_ip, {}))


class RedisCache(Cache):
    def __init__(self):
        raise NotImplementedError


class ClientCache(Cache):
    def __init__(self, data):
        self.cache = data

    def add_url(self, url, host=None):
        # unescape URL
        try:
            unescaped_url = bytes(url, 'ascii').decode('unicode_escape')
        except UnicodeDecodeError:
            unescaped_url = url

        unquoted_url = urllib.parse.unquote_plus(unescaped_url)
        scheme, netloc, path, query, frag = urllib.parse.urlsplit(unquoted_url)

        if netloc or not host:
            host = netloc

        rel_url = urllib.parse.urlunsplit(('', '', path, query, frag))
        self.cache.setdefault(host, {})\
                  .setdefault('rel_urls', set([]))\
                  .add(rel_url)

    def has_url(self, host, rel_url):
        try:
            return urllib.parse.unquote_plus(rel_url) in self.cache[host]['rel_urls']
        except KeyError:
            return False
        else:
            return False

    def add_cookie(self, host, cookie):
        self.cache.setdefault(host, {})\
                  .setdefault('cookies', set([]))\
                  .add(cookie)

    def has_cookie(self, host, cookie):
        try:
            return cookie in self.cache[host]['cookies']
        except KeyError:
            return False
        else:
            return False

    def has_domain(self, host):
        try:
            return self.cache[host]
        except KeyError:
            return False
