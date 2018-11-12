import abc
import asyncio


class Proxy(abc.ABC):
    protocol = None

    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        return

    @classmethod
    async def main(cls, port, cli_args, *args, **kwargs):
        proxy = cls(*args, **kwargs)
        server = await asyncio.start_server(proxy, port=port)

        print("Serving {protocol} on {port}...".format(protocol=cls.protocol,
                                                       port=port))

        async with server:
            await server.serve_forever()
