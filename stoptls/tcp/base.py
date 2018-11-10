import socket
import struct
from abc import ABC, abstractmethod


class TCPProxy(ABC):
    SO_ORIGINAL_DST = 80

    def __init__(self):
        super().__init__()

    @abstractmethod
    async def strip(self, client_reader, client_writer):
        raise NotImplementedError

    def get_orig_dst_socket(self, writer):
        sock = writer.get_extra_info('socket')
        sockaddr_in = sock.getsockopt(socket.SOL_IP,
                                      TCPProxy.SO_ORIGINAL_DST,
                                      16)
        port, = struct.unpack('!h', sockaddr_in[2:4])
        address = socket.inet_ntoa(sockaddr_in[4:8])
        return address, port
