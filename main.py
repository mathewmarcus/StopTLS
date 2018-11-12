import asyncio
import argparse

from stoptls.web import HTTPProxy
from stoptls.tcp import TCPProxy


parser = argparse.ArgumentParser(add_help='--help',
                                 conflict_handler='resolve',
                                 description='MitM proxy which performs \
                                 opportunistic SSL/TLS stripping')
parser.add_argument('-h', '--http',
                    type=int,
                    nargs='?',
                    const=10000,
                    dest='http_port',
                    help='HTTP listen port [default: %(const)i]')
parser.add_argument('-t', '--tcp',
                    type=int,
                    nargs='?',
                    const=49151,
                    dest='tcp_port',
                    help='TCP listen port [default: %(const)i]')
parser.add_argument('-p', '--tcp-protocols',
                    default=['SMTP', 'IMAP'],
                    nargs='+',
                    choices=['SMTP', 'IMAP'],
                    help='supported TCP protocols')

if __name__ == '__main__':
    args = parser.parse_args()

    if not (args.http_port or args.tcp_port):
        parser.print_help()
        print('\nSelect -h [HTTP_PORT],--http [HTTP_PORT] and/or -t [TCP_PORT],--tcp [TCP_PORT]')
        exit(1)

    loop = asyncio.get_event_loop()

    if args.http_port:
        asyncio.ensure_future(HTTPProxy.main(args.http_port,
                                             args))
    if args.tcp_port:
        asyncio.ensure_future(TCPProxy.main(args.tcp_port,
                                            args))
    loop.run_forever()
