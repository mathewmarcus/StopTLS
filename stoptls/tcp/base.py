import asyncio
import socket
import ssl
import logging
import abc


class TCPProxyConn(abc.ABC):
    protocol = None
    ports = None
    command_re = None
    response_re = None
    starttls_re = None

    def __init__(self, client_reader, client_writer,
                 server_reader, server_writer):
        self.client_reader = client_reader
        self.client_writer = client_writer
        self.server_reader = server_reader
        self.server_writer = server_writer
        super().__init__()

    @abc.abstractmethod
    async def strip(self):
        self.server_writer.close()
        self.client_writer.close()
        logging.debug('Connections closed')

    async def upgrade_connection(self):
        sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        sc.check_hostname = False
        sc.verify_mode = ssl.CERT_NONE

        try:
            nameinfo = await asyncio.get_running_loop()\
                                    .getnameinfo(self.server_writer.get_extra_info('peername'),
                                                 socket.NI_NAMEREQD)
            self.server_reader, self.server_writer = await asyncio \
                                    .open_connection(sock=self.server_writer.get_extra_info('socket'),
                                                     ssl=sc,
                                                     server_hostname=nameinfo[0])
            return True
        except Exception:
            logging.exception('Failed to upgrade to TLS')
            return False
