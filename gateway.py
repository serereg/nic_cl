from utils import timer


class Gateway:
    def __init__(self, uri, opc=None):
        self.uri = uri
        self.opc = opc
        self.ws = None
    
    @timer(0)
    async def check_ws(self):
        async with ClientSession() as session, session.ws_connect(self.uri) as self.ws:
            while True:
                await asyncio.sleep(0.1)
                if self.ws.closed:
                    return

    @timer(5)
    async def to_server(self):
        data = {"method": "state", "params": {}}
        for cooler in self.opc.coolers:
            data["params"][cooler.name] = {
                "temperature": cooler.pv.Value,
                "sp": cooler.sp,
                "is_on": cooler.isOn(),
                "state": cooler.State,
            }

        await self.ws.send_json(data)

    async def from_server(self):
        async for message in self.ws:
            pass

    async def run(self, loop):
        return (
            loop.create_task(self.check_ws),
            loop.create_task(self.to_server),
            loop.create_task(self.from_server),
        )
