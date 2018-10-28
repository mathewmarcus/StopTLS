import asyncio
from stoptls.web import main as web_main
from stoptls.tcp import main as generic_tcp_main


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(web_main())
    asyncio.ensure_future(generic_tcp_main())
    loop.run_forever()
