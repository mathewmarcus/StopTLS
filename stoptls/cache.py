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

    def add_url(self, remote_socket, url):
        # TODO: handler cases where URL has escape characters
        parsed_url = urllib.parse.urlsplit(url)
        rel_url = ''.join(parsed_url[2:4])
        self.cache.setdefault(remote_socket, {})\
                  .setdefault(parsed_url[1], {})\
                  .setdefault('rel_urls', set([]))\
                  .add(rel_url)

    def has_url(self, remote_socket, host, rel_url):
        try:
            return rel_url in self.cache[remote_socket][host]['rel_urls']
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


class RedisCache(Cache):
    def __init__(self):
        raise NotImplementedError
