import asyncio
import functools
import collections

#for import Cooler
import json
import sys
import os
sys.path.append(os.path.abspath("../../srv/pargolovo_server/ajax_sample"))
from Cooler import Cooler
#from ../../srv/pargolovo_server/ajax_sample import Cooler

#for workin with opc
import OpenOPC
import pywintypes
from aiohttp import ClientSession
from loguru import logger


# for working with telegram
import traceback
import time
import sys

import siotelegram
import requests


# logger.add(sys.stderr)

TOKEN = "955648204:AAGGyUALGcG7Xt3cwYB5hMY06_1-7vwoLk0"
# telegram init
api = siotelegram.RequestsTelegramApi(TOKEN, timeout=10, proxy="socks5h://127.0.0.1:9150")


def run_in_executor(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, f, *args, **kwargs)
    return wrapper


class OPC:
    def __init__(self, base_name, items):
        self.base_name = base_name
        self.items = items
        self.coolers_arr = [Cooler(c) for c in range(1, 13)]
        # Connect to OPC
        pywintypes.datetime=pywintypes.TimeType
        # self.opc = OpenOPC.client()
        # self.opc.connect(base_name)

    @run_in_executor
    def get_temperature(self, index):
        try:
            for c in self.coolers_arr:
                if c.name == index:
                    opc_package = self.opc.read(c.pv.TagName)
                    if (opc_package[1] == 'Good'):
                        c.pv.Value = opc_package[0]
                        c.pv.Fault = False
                    else:
                        c.pv.Value = -111.1
                        c.pv.Fault = True

                    opc_package = self.opc.read(c.TagSP)
                    if (opc_package[1] == 'Good'):
                        c.sp = opc_package[0]
                    else:
                        c.sp = -111.1

                    # opc_package = self.opc.read(c.TagState)
                    # if (opc_package[1] == 'Good'):
                    #     c.State = opc_package[0]
                    # else:
                    #     c.State = -666.6
                    break
                
        except Exception:
            # print('exception opc get_temperature')
            c.pv.Value = -321.1
            c.pv.Fault = True
            c.sp = -321.1
            c.State = -321.1
        return c.pv.Value
  
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
        self.home_id = None
        self._ws_connected = asyncio.Event()

    @timer(10)
    async def _receive_commands_from_web_srv_task(self):
        logger.info("enter command handler")
        async for msg in self.ws:
            logger.info("opc command {}", msg.data)
            data = json.loads(msg.data)
            if data["type"] != "command":
                continue
            command = data["command"]
            if command == "set_sp":
                pass
            elif command == "YOn":
                pass
            elif command == "YOff":
                pass
            else:
                logger.error("Unsupported command {}", command)

    @timer(10)
    async def _read_opc_task(self, item):
        # logger.info("read tempearture {} \n", item)
        self._current_temperature[item] = await self.opc.get_temperature(item)

    @timer(10)
    async def _send_temperature_to_web_srv_task(self):
        for item, t in self._current_temperature.items():
            #logger.info("sending {} temperature {} \n\n", item, t)
            await self.ws.send_json(dict(type="temperature", item=item, temperature=t))
            # await self.ws.send_json(dict(type="temperature2", item=item, temperature=t))

    @timer(5)
    async def _send_temperatures_to_telegram(self):
        values = ''
        i = 0
        
        response = api.get_updates()

        for item, t in self._current_temperature.items():
            values = values + item + " T= " + str(self.opc.coolers_arr[i].pv.Value) + '\n'
            if self.opc.coolers_arr[i].pv.Value != self.opc.coolers_arr[i].sp or self.opc.coolers_arr[i].pv.Fault:
                if not self.opc.coolers_arr[i].Alarm:
                    api.send_message(chat_id=self.home_id, text=self.opc.coolers_arr[i].name + " T= " + str(self.opc.coolers_arr[i].pv.Value))
                self.opc.coolers_arr[i].Alarm = True
            else:
                self.opc.coolers_arr[i].Alarm = False
            i = i + 1
        try:
            for r in response["result"]:
                json = requests.get("https://api.ipify.org?format=json").json()
                api.send_message(chat_id=r["message"]["chat"]["id"], text=json["ip"])  # read ip
                print(json["ip"])
                # values = str(opc.read('Request1.TIC1_YOn'))# read value
                api.send_message(chat_id=r["message"]["chat"]["id"], text=values)
                self.home_id = r["message"]["chat"]["id"]
                print(values)

        except Exception:
            traceback.print_exc()
        time.sleep(1)

    @timer(0)
    async def _ensure_web_socket(self):
        async with ClientSession() as session:
            async with session.ws_connect(self.url) as self.ws:
                self._ws_connected.set()
                logger.info("web socket ready")
                while True:
                    await asyncio.sleep(0.1)
                    if self.ws.closed:
                        return

    async def run(self):
        self.tasks = [
            asyncio.create_task(self._ensure_web_socket()),
        ]
        await self._ws_connected.wait()
        self.tasks.extend([
            asyncio.create_task(self._receive_commands_from_web_srv_task()),
            asyncio.create_task(self._send_temperature_to_web_srv_task()),

            asyncio.create_task(self._send_temperatures_to_telegram()), # telegram
        ])
        for item in self.opc.items:
            self.tasks.extend([
                asyncio.create_task(self._read_opc_task(item)),
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
