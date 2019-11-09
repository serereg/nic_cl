import OpenOPC
import pywintypes

import traceback
import time

import siotelegram
import requests


TOKEN = "955648204:AAGGyUALGcG7Xt3cwYB5hMY06_1-7vwoLk0"




def main():
    api = siotelegram.RequestsTelegramApi(TOKEN, timeout=10, proxy="socks5h://127.0.0.1:9150")
    while True:
        try:
            response = api.get_updates()
            for r in response["result"]:
                json = requests.get("https://api.ipify.org?format=json").json()
                api.send_message(chat_id=r["message"]["chat"]["id"], text=json["ip"]) # read ip
                print(json["ip"])
                values = str(opc.read('Request1.TIC1_YOn'))# read value
                values = values + " dfa\n"
                api.send_message(chat_id=r["message"]["chat"]["id"], text=values) 
                print(values)
        except Exception:
            traceback.print_exc()
        time.sleep(1)

# Connect to OPC
pywintypes.datetime=pywintypes.TimeType
opc=OpenOPC.client()
opc.connect('Lectus.OPC.1')
# print(opc.read('Node.Item1'))

if __name__ == "__main__":
    main()
