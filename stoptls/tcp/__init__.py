import asyncio
import socket
import struct
import logging

from stoptls.tcp.IMAP import IMAPProxyConn
from stoptls.tcp.smtp import SMTPProxyConn


class TCPProxy(object):
    SO_ORIGINAL_DST = 80

    def __init__(self, *proxy_conn_factories, **cli_args):
        # TODO: process command line arguments
        self.conn_switcher = {
            '25': SMTPProxyConn,
            '143': IMAPProxyConn,
            '587': SMTPProxyConn
        }
        super().__init__()

    async def __call__(self, client_reader, client_writer):
        dst_addr, dst_port = self.get_orig_dst_socket(client_writer)
        logging.debug('Original destination: {}:{}'.format(dst_addr, dst_port))
        server_reader, server_writer = await asyncio.open_connection(dst_addr,
                                                                     dst_port)
        try:
            self.conn_switcher[dst_port](client_reader, client_writer,
                                         server_reader, server_writer).strip()
        except KeyError as e:
            raise Exception('No handler set up for destination port: {}'
                            .format(dst_port))

    def get_orig_dst_socket(self, client_writer):
        sock = client_writer.get_extra_info('socket')
        sockaddr_in = sock.getsockopt(socket.SOL_IP,
                                      TCPProxy.SO_ORIGINAL_DST,
                                      16)
        port, = struct.unpack('!h', sockaddr_in[2:4])
        address = socket.inet_ntoa(sockaddr_in[4:8])
        return address, port

    @classmethod
    async def main(cls, port, **cli_args):
        proxy = cls(**cli_args)
        server = await asyncio.start_server(proxy, port=port)

        print("Serving {protocol} on {port}...".format(protocol=cls.__name__,
                                                       port=port))

        async with server:
            await server.serve_forever()
