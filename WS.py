import asyncio
import collections
import functools

import json
from tor import TorSocketProcess

from aiohttp import ClientSession
from loguru import logger

import sys
import time
import traceback
from threading import Thread
# for working with telegram
import requests
import siotelegram

# telegram init
api = siotelegram.RequestsTelegramApi(obj["TOKEN"], timeout=10, proxy="socks5h://127.0.0.1:9050")

from utils import JSONRPCView

class WS(JSONRPCView):

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
        self.home_id = "700566535"
        self._ws_connected = asyncio.Event()
        self.wdt = 0 # diagnostic timer
        self.telegram_alarms = [False for _ in range(12)]

    @timer(10)
    async def _receive_commands_from_web_srv_task(self):
        # logger.info("enter command handler")print(msg.data)
        async for message in self.ws:
            result, response_required = await self.handle(message.data, {})
            if response_required:
                await self.ws.send_json(result)

    async def command(self, id, switch):
        print("command ok")
        if switch == "YOn":
            pass
            #     self.opc.write_cmd_on(data["target"])
        elif switch == "YOff":
            pass
            #     self.opc.write_cmd_off(data["target"])
        else:
            logger.error("Unsupported command {}", command)
        return "ok", None

    async def set_point(self, id, set_point):
        print("set_point ok")
        # self.opc.write_sp(data["value"], data["target"])
        return "ok", None

    def _read_opc_task(self, c_index):
        # logger.info("read tempearture {} \n", item)
        while self.read_opc_task_running:
            try:
                self._current_temperature[c_index.name] = self.opc.get_temperature(c_index)  #  await
                print(self._current_temperature)
            except Exception as e:
                print("ERROR:", e)
                pass
            time.sleep(5)

    def read_all_sensors(self):
        for c_item in self.opc.coolers_arr:
            try:
                self._current_temperature[c_item.name] = self.opc.get_temperature(c_item)
                print(self._current_temperature)
            except Exception as e:
                print("ERROR:", e)
                pass
            time.sleep(1)

    @timer(10)
    async def _send_temperature_to_web_srv_task(self):
        self.wdt = self.wdt + 1
        if self.wdt > 10000 or self.wdt < 0:
            self.wdt = 0
        for c_item in self.opc.coolers_arr:
            pack = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "state",
                "params": {
                    "item": c_item.name,
                    "temperature": c_item.GetPV(),
                    "set_point": c_item.sp,
                    "state": c_item.State,
                    "wdt": self.wdt,
                },
            }
            await self.ws.send_json(pack)
            print(pack)
            
    @timer(5)
    async def _send_temperatures_to_telegram(self):
        values = 'response\n'
        i = 0

        print("TELEGRAM COROUTINE")
        response = api.get_updates()

        # TODO: use Jinja template 
        for item, t in self._current_temperature.items():
            cur_cooler = self.opc.coolers_arr[i]
            values = values + item + " T= " + str(cur_cooler.pv.Value) + '\n'
            if self.telegram_alarms[i] == False and cur_cooler.Alarm == True:
                api.send_message(chat_id=self.home_id, text=cur_cooler.name + ", T= " + str(cur_cooler.pv.Value) + ", SP= " + str(cur_cooler.sp))
            self.telegram_alarms[i] = cur_cooler.Alarm
            i = i + 1

        try:
            for r in response["result"]:
                print("RESULT OF TELEGRAM COROUTINE")
                api.send_message(chat_id = self.home_id, text = values)

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

        threads = []
        self.read_opc_task_running = True
        # for c_item in self.opc.coolers_arr:
        #     t = Thread(target=self._read_opc_task, args=(c_item,))
        #     threads.append(t)
        #     t.start()

        
        t = Thread(target=self.read_all_sensors)
        t.start()

        await asyncio.wait(self.tasks)
        for t in self.tasks:
            t.cancel()
        # await asyncio.wait(self.tasks)
