import asyncio
import socket
import struct
import logging

from stoptls.base import Proxy
from stoptls.tcp.imap import IMAPProxyConn
from stoptls.tcp.smtp import SMTPProxyConn


class TCPProxy(Proxy):
    protocol = 'TCP'
    SO_ORIGINAL_DST = 80
    proxy_connection_handlers = {IMAPProxyConn.protocol: IMAPProxyConn,
                                 SMTPProxyConn.protocol: SMTPProxyConn}

    def __init__(self, connection_handlers):
        # TODO: process command line arguments
        self.conn_switcher = {}
        for handler in connection_handlers:
            for port in handler.ports:
                logging.debug('Egress port {}: {}'.format(port, handler))
                self.conn_switcher[port] = handler
        super().__init__()

    async def __call__(self, client_reader, client_writer):
        dst_addr, dst_port = self.get_orig_dst_socket(client_writer)
        logging.debug('Original destination: {}:{}'.format(dst_addr, dst_port))
        server_reader, server_writer = await asyncio.open_connection(dst_addr,
                                                                     dst_port)
        try:
            conn = self.conn_switcher[dst_port](client_reader, client_writer,
                                                server_reader, server_writer)
            logging.debug('Handling connection to {}:{}'.format(dst_addr,
                                                                dst_port))
            await conn.strip()
        except KeyError as e:
            raise Exception('No handler set up for destination port: {}'
                            .format(dst_port))

    def get_orig_dst_socket(self, client_writer):
        sock = client_writer.get_extra_info('socket')
        sockaddr_in = sock.getsockopt(socket.SOL_IP,
                                      TCPProxy.SO_ORIGINAL_DST,
                                      16)
        port, = struct.unpack('!H', sockaddr_in[2:4])
        address = socket.inet_ntoa(sockaddr_in[4:8])
        return address, port

    @classmethod
    async def main(cls, port, cli_args, *args, **kwargs):
        conn_handlers = (cls.proxy_connection_handlers[p] for p in cli_args.tcp_protocols)

        await super().main(port, cli_args, connection_handlers=conn_handlers)
