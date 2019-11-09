import asyncio
import functools
import collections


import sys
import os
sys.path.append(os.path.abspath("../../srv/pargolovo_server/ajax_sample"))
from Cooler import Cooler
#from ../../srv/pargolovo_server/ajax_sample import Cooler


import OpenOPC
import pywintypes
from aiohttp import ClientSession
from loguru import logger


class OPC:
    def __init__(self, base_name, items):
        self.base_name = base_name
        self.items = items
        self.coolers_arr = [Cooler(c) for c in range(1, 13)]
        # self.coolers_arr = [Cooler(1), Cooler(2), Cooler(3), Cooler(4), Cooler(5), Cooler(6), Cooler(7), Cooler(8), Cooler(9), Cooler(10), Cooler(11), Cooler(12)]
        # Connect to OPC
        pywintypes.datetime=pywintypes.TimeType
        self.opc = OpenOPC.client()
        self.opc.connect(base_name)

    async def get_temperature(self, index):
        # import random
        values = 123
        try:
            for c in range(1, 13):
                #print(self.coolers_arr[c].name)
                if self.coolers_arr[c].name == index:
                    #print(self.coolers_arr[c].pv.TagName)
                    opc_package = self.opc.read(self.coolers_arr[c].pv.TagName)
                    values = opc_package[0]  # self.coo.GetPV()  # str(opc.read('Node.'+self.items[index]))# read value
                    break

        except Exception:
            values = -321.1
        # return random.randint(-20, 20)
        return values


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
        #logger.info("read tempearture {} \n", item)
        self._current_temperature[item] = await self.opc.get_temperature(item)

    @timer(10)
    async def _send_temperatures_task(self):
        for item, t in self._current_temperature.items():
            #logger.info("sending {} temperature {} \n\n", item, t)
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
    opc = OPC("Lectus.OPC.1", ["CKT1", "CKT2", "CKT3", "CKT4", "CKT5", "CKT6",
                               "CKT7", "CKT8", "CKT9", "CKT10", "CKT11", "CKT12"])
    ws = WS("http://localhost:8080/ws/opc", opc)
    await ws.run()

if __name__ == "__main__":
    asyncio.run(main())
