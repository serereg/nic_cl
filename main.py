import asyncio
from threading import Thread

from cooler.cooler import Cooler
from opc import OPC

from tor import TorSocketProcess

from WS import WS
from OPCClient import OPCClient

# logger.add(sys.stderr)

# TOKEN = "955648204:AAGGyUALGcG7Xt3cwYB5hMY06_1-7vwoLk0"

async def main():
    opc = OPC("localhost", range(8)) 
    # ws = WS("http://serereg.hopto.org:8080/ws/opc", opc)
    ws = WS("http://localhost:80/ws/opc", opc)
    await ws.run()

if __name__ == "__main__":
    # process = TorSocketProcess()
    # process.start()
    asyncio.run(main())
