import asyncio
import argparse

from stoptls.web import HTTPProxy
from stoptls.tcp import TCPProxy


parser = argparse.ArgumentParser(description='MitM proxy which performs opportunistic SSL/TLS stripping')
parser.add_argument('--http-port',
                    type=int,
                    default=8080,
                    help='HTTP listen port')
parser.add_argument('-t', '--tcp-port',
                    type=int,
                    default=49151,
                    help='TCP listen port')
parser.add_argument('-p', '--tcp-protocols',
                    default=['smtp', 'imap'],
                    nargs='+',
                    help='supported TCP protocols')


if __name__ == '__main__':
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(HTTPProxy.main(args.http_port,
                                         args))
    asyncio.ensure_future(TCPProxy.main(args.tcp_port,
                                        args))
    loop.run_forever()
