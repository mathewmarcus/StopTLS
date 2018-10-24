import asyncio
import socket


dns_cache = {}


async def dns_resolve(hostname):
    try:
        return dns_cache[hostname]
    except KeyError:
        addrinfo = await asyncio.get_running_loop().getaddrinfo(hostname,
                                                                None,
                                                                family=socket.AF_INET,
                                                                type=socket.SOCK_STREAM,
                                                                proto=socket.SOL_TCP)
        return addrinfo[0][4][0]
