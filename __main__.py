import asyncio
import functools
import collections

#for import Cooler
import json
from Cooler import Cooler
from opc import OPC

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


# https://github.com/torpyorg/torpy
# torpy_socks -p 1050 --hops 3
# https://github.com/torpyorg/torpy/blob/master/torpy/cli/socks.py#L168

class OPCClient:
    def __init__(self, url, opc, telegram_token):
        self.url = url
        self.opc = opc
        self.ws = None
        self.telegram_client = siotelegram.RequestsTelegramApi(telegram_token, timeout=10, proxy="socks5h://127.0.0.1:9150")
        self.alarms = set()
        self.chat_id = None
    
    async def to_server(self):
        data = {"method": "state", "params": {}}
        for cooler in self.opc.coolers_arr:
            data["params"][cooler.name] = {
                "temperature": cooler.pv.Value,
                "sp": cooler.sp,
                "is_on": cooler.isOn(),
                "state": cooler.State,
            }

        async with ClientSession() as session, session.ws_connect(self.url) as ws:
            ws.send_json(data)

    async def to_telegram(self):
        updates = self.telegram_client.get_updates()
        values = []

        for cooler in self.opc.coolers_arr:
            text = f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}"
            values.append(text)
            if cooler.Alarm and cooler not in self.alarms:
                self.telegram_client.send_message(chat_id=self.chat_id, text=text)
            self.alarms.add(cooler) if cooler.Alarm else self.alarms.remove(cooler)

        try:
            for r in response["result"]:
                self.telegram_client.send_message(chat_id=r["message"]["chat"]["id"], text="\n".join(values))
                self.chat_id = r["message"]["chat"]["id"]

        except Exception:
            traceback.print_exc()
        await asyncio.sleep(1)



class WS:

    def timer(interval):
        def decorator(f):
            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                while True:
                    try:
                        await f(*args, **kwargs)
                    except asyncio.CancelledError as e:
                        raise e
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
        self.wdt = 0 # diagnostic timer
        self.telegram_alarms = [False for _ in range(12)]

    @timer(10)
    async def _receive_commands_from_web_srv_task(self):
        logger.info("enter command handler")
        async for msg in self.ws:
            logger.info("opc command {}", msg.data)
            print(msg.data)
            data = json.loads(msg.data)
            if data["type"] != "command":
                continue
            command = data["command"]
            if command == "set_sp":
                self.opc.write_sp(data["value"], data["target"])
            elif command == "YOn":
                self.opc.write_cmd_on(data["target"])
            elif command == "YOff":
                self.opc.write_cmd_off(data["target"])
            else:
                logger.error("Unsupported command {}", command)

    @timer(10)
    async def _read_opc_task(self, c_index):
        # logger.info("read tempearture {} \n", item)
        self._current_temperature[c_index.name] = self.opc.get_temperature(c_index)  #  await

    @timer(10)
    async def _send_temperature_to_web_srv_task(self):
        self.wdt = self.wdt + 1
        if self.wdt > 10000 or self.wdt < 0:
            self.wdt = 0
        for c_item in self.opc.coolers_arr:
            pack = dict(type="temperature", item=c_item.name, temperature=c_item.GetPV(), sp=c_item.sp, is_on=c_item.isOn(), state=c_item.State, wdt=self.wdt)
            await self.ws.send_json(pack)
            print(pack)
            
    @timer(5)
    async def _send_temperatures_to_telegram(self):
        values = ''
        i = 0

        response = api.get_updates()

        for item, t in self._current_temperature.items():
            cur_cooler = self.opc.coolers_arr[i]
            values = values + item + " T= " + str(cur_cooler.pv.Value) + '\n'
            if self.telegram_alarms[i] == False and cur_cooler.Alarm == True:
                api.send_message(chat_id=self.home_id, text=cur_cooler.name + ", T= " + str(cur_cooler.pv.Value) + ", SP= " + str(cur_cooler.sp))
            self.telegram_alarms[i] = cur_cooler.Alarm
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
        async with ClientSession() as session, session.ws_connect(self.url) as self.ws:
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
        for c_item in self.opc.coolers_arr:
            self.tasks.extend([
                asyncio.create_task(self._read_opc_task(c_item)),
            ])

        await asyncio.wait(self.tasks)
        for t in self.tasks:
            t.cancel()
        await asyncio.wait(self.tasks)


async def main():


    opc = OPC("localhost", range(8)) 
    ws = WS("http://serereg.hopto.org:8080/ws/opc", opc)
    #ws = WS("http://localhost:8080/ws/opc", opc)
    await ws.run()

if __name__ == "__main__":
    asyncio.run(main())
