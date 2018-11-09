import socket
from abc import ABC, abstractmethod


class TCPProxy(ABC):
    SO_ORIGINAL_DST = 80

    def __init__(self):
        super().__init__()

    @abstractmethod
    async def strip(self, reader, writer):
        raise NotImplementedError

    def get_orig_ip(self, reader):
        sock = reader._transport.get_extra_info('socket')
        sockaddr_in = sock.getsockopt(socket.SOL_IP,
                                      TCPProxy.SO_ORIGINAL_DST,
                                      16)
        address = socket.inet_ntoa(sockaddr_in[4:8])
        return address
