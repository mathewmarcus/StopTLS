import asyncio
import argparse

from stoptls.web import main as web_main
from stoptls.tcp import TCPProxy


parser = argparse.ArgumentParser(description='MitM proxy which performs opportunistic SSL/TLS stripping')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(web_main())
    asyncio.ensure_future(TCPProxy.main(14314))
    loop.run_forever()
