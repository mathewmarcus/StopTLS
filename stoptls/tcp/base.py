import asyncio
import socket
import ssl
import logging
import abc


class TCPProxyConnection(abc.ABC):
    ports = None
    command_re = None
    response_re = None

    def __init__(self, client_reader, client_writer,
                 server_reader, server_writer):
        self.client_reader = client_reader
        self.client_writer = client_writer
        self.server_reader = server_reader
        self.server_writer = server_writer
        super().__init__()

    @abc.abstractmethod
    async def strip(self):
        return

    async def start_tls(self):
        self.server_writer.write('STARTTLS\n'.encode('ascii'))
        await self.server_writer.drain()

        tls_started = await self.server_reader.readline()
        tls_started_re = type(self).response_re.fullmatch(tls_started.decode('ascii'))

        if tls_started_re and \
           tls_started_re.group('status_code') == '220':
            sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            sc.check_hostname = False
            sc.verify_mode = ssl.CERT_NONE

            nameinfo = await asyncio.get_running_loop()\
                                    .getnameinfo(self.server_writer.get_extra_info('peername'),
                                                 socket.NI_NAMEREQD)
            self.server_reader, self.server_writer = await asyncio \
                                    .open_connection(sock=self.server_writer.get_extra_info('socket'),
                                                     ssl=sc,
                                                     server_hostname=nameinfo[0])
            logging.debug('Sucessfully upgraded to TLS!')
            return True
        else:
            logging.debug('Failed to upgraded to TLS')
            return False
