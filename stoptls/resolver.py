import asyncio
import socket


dns_cache = {}


async def dns_resolve(hostname):
    hostname = hostname.split(':')[0]
    try:
        return dns_cache[hostname]
    except KeyError:
        addrinfo = await asyncio.get_running_loop().getaddrinfo(hostname,
                                                                None,
                                                                family=socket.AF_INET,
                                                                type=socket.SOCK_STREAM,
                                                                proto=socket.SOL_TCP)
        ip = addrinfo[0][4][0]
        dns_cache[hostname] = ip
        return ip
