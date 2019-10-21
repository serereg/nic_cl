import asyncio
import functools
import collections

# import OpenOPC
# import pywintypes
from aiohttp import ClientSession
from loguru import logger


class OPC:

    def __init__(self, base_name, items):
        self.base_name = base_name
        self.items = items

    async def get_temperature(self, index):
        import random
        return random.randint(-20, 20)


class WS:

    def timer(interval):
        def decorator(f):
            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                while True:
                    try:
                        await f(*args, **kwargs)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("Exception in {}", f.__name__)
                    await asyncio.sleep(interval)
            return wrapper
        return decorator

    def __init__(self, url, opc):
        self.url = url
        self.opc = opc
        self.ws = None
        self._current_temperature = collections.defaultdict(lambda: None)

    @timer(10)
    async def _receive_commands_task(self):
        async for msg in self.ws:
            logger.info("opc command {}", msg.data)

    @timer(10)
    async def _read_temperature_task(self, item):
        logger.info("read tempearture {}", item)
        self._current_temperature[item] = await self.opc.get_temperature(item)

    @timer(10)
    async def _send_temperatures_task(self):
        for item, t in self._current_temperature.items():
            logger.info("sending {} temperature {}", item, t)
            await self.ws.send_json(dict(type="temperature", item=item, temperature=t))

    async def run(self):
        async with ClientSession() as session:
            async with session.ws_connect(self.url) as self.ws:
                self.tasks = [
                    asyncio.create_task(self._receive_commands_task()),
                    asyncio.create_task(self._send_temperatures_task()),
                ]
                for item in self.opc.items:
                    self.tasks.extend([
                        asyncio.create_task(self._read_temperature_task(item)),
                    ])
                await asyncio.wait(self.tasks)
                for t in self.tasks:
                    t.cancel()
                await asyncio.wait(self.tasks)


async def main():
    opc = OPC("Lectus.OPC.1", ["item1", "item2"])
    ws = WS("http://localhost:8080/ws/opc", opc)
    await ws.run()

if __name__ == "__main__":
    asyncio.run(main())
