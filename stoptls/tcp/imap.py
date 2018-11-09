import asyncio
import logging

from stoptls.tcp.base import TCPProxy

logging.getLogger().setLevel(logging.DEBUG)


class IMAPProxy(TCPProxy):
    def __init__(self):
        super().__init__(dst_port=143)

    async def strip(self, client_reader, client_writer):
        dst_address = self.get_orig_ip(client_reader)
        dst_address = '127.0.0.1'
        logging.debug('Original destination: {}'.format(dst_address))
        server_reader, server_writer = await asyncio.open_connection(dst_address,
                                                                     self.dst_port)
        banner = await server_reader.readline()
        logging.debug('Received banner: {}'.format(banner))
        client_writer.write(banner)
        logging.debug('Writing banner to client...')
        await client_writer.drain()

        while not server_reader.at_eof():
            client_data = await client_reader.readline()
            logging.debug('Received client data: {}'.format(client_data))

            if client_reader.at_eof():
                logging.debug('Client closed connection')
                break

            tag = client_data[0]
            server_writer.write(client_data)
            logging.debug('Writing client data to server...')
            await server_writer.drain()

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

                if server_data[0] == tag:
                    break

        server_writer.close()
        client_writer.close()
        logging.debug('Connections closed')
