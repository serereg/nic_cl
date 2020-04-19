from utils import timer, JSONRPCView
from aiohttp import web, ClientSession
import asyncio

class Gateway(JSONRPCView):
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
                
                pack = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "state",
                    "params": {
                        "item": cooler.name,
                        "temperature": cooler.GetPV(),
                        "set_point": cooler.sp,
                        "state": cooler.State,
                        "wdt": self.wdt,
                    },
                }
                await self.ws.send_json(pack)

        # await self.ws.send_json(data)

    @timer(1)
    async def from_server(self):
        async for message in self.ws:
            result, response_required = await self.handle(message.data, {})
            if response_required:
                await self.ws.send_json(result)

    # TODO: заменить на прямой вызов opc
    async def command(self, id, switch):
        print("command ok")
        if self.opc:
            if switch == "YOn":
                self.opc.write_cmd_on(f"CKT{id}")
            elif switch == "YOff":
                self.opc.write_cmd_off(f"CKT{id}")
            else:
                logger.error("Unsupported command {}", command)
        return "ok", None

    # TODO: заменить на прямой вызов opc
    async def set_point(self, id, set_point):
        print("set_point ok")
        if self.opc:
            self.opc.write_sp(set_point, f"CKT{id}")
        return "ok", None
                
    def start(self, loop):
        return (
            loop.create_task(self.check_ws()),
            loop.create_task(self.to_server()),
            loop.create_task(self.from_server()),
        )
