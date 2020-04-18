from utils import timer
from aiohttp import web, ClientSession
import asyncio

class Gateway:
    def __init__(self, uri, opc=None):
        self.uri = uri
        self.opc = opc
        self.ws = None
        self.wdt = 0
    
    @timer(0)
    async def check_ws(self):
        async with ClientSession() as session, session.ws_connect(self.uri) as self.ws:
            while True:
                await asyncio.sleep(0.1)
                if self.ws.closed:
                    return

    @timer(5)
    async def to_server(self):
        self.wdt += 1
        if self.wdt > 10000 or self.wdt < 0:
            self.wdt = 1
        data = {
            "jsonrpc": "2.0",
            "id": self.wdt,
            "method": "state",
            "params": {},
        }

        if self.opc:
            for cooler in self.opc.coolers:
                data["params"][cooler.name] = {
                    "item": cooler.name,
                    "temperature": cooler.GetPV(),
                    "set_point": cooler.sp,
                    "state": cooler.State,
                    "wdt": self.wdt,
                }

        await self.ws.send_json(data)

    async def from_server(self):
        async for message in self.ws:
            pass

    def start(self, loop):
        return (
            loop.create_task(self.check_ws()),
            loop.create_task(self.to_server()),
            loop.create_task(self.from_server()),
        )
