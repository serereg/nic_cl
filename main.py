import asyncio

from config import CONFIG
from cooler.cooler import Cooler
from gateway import Gateway
from opc import OPC
from telegram import TelegramClient
from tor import TorSocketProcess


if __name__ == "__main__":
    opc = None
    data = CONFIG["opc"]
    if data["enable"]:
        opc = OPC(host=data["host"], port=data["port"], cooler_count=12)
        # opc.start()

    tor = None
    data = CONFIG["tor"]
    if data["enable"]:
        tor = TorSocketProcess(ip=data["ip"], port=data["port"], hops=data["hops"])
        tor.start()

    telegram = None
    data = CONFIG["telegram"]
    if data["enable"]:
        telegram = TelegramClient(opc=opc, token=data["token"], chat_id=data["chat_id"], tor=tor)

    gateway = None
    data = CONFIG["server"]
    if data["enable"]:
        gateway = Gateway(uri=data["uri"], opc=opc)

    loop = asyncio.get_event_loop()
    tasks = []
    
    if opc is not None:
        tasks.extend(opc.start(loop))
    if telegram is not None:
        tasks.extend(telegram.start(loop))
    if gateway is not None:
        tasks.extend(gateway.start(loop))

    loop.run_until_complete(asyncio.wait(tasks))
