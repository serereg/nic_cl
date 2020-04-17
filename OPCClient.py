class OPCClient:
    def __init__(self, url, opc, telegram_token, chat_id):
        self.url = url
        self.opc = opc
        self.ws = None
        self.telegram_client = siotelegram.RequestsTelegramApi(telegram_token, timeout=10, proxy="socks5h://127.0.0.1:9050")
        self.alarms = set()
        self.chat_id = chat_id
        self.tor_client = TorClient()
    
    async def to_server(self):
        data = {"method": "state", "params": {}}
        for cooler in self.opc.coolers_arr:
            data["params"][cooler.name] = {
                "temperature": cooler.pv.Value,
                "sp": cooler.sp,
                "is_on": cooler.isOn(),
                "state": cooler.State,
            }

        self.ws.send_json(data)

    async def from_server(self):
        async for message in self.ws:
            pass

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

    async def update(self):
        for cooler in self.opc.coolers_arr:
            self.opc.get_temperature(cooler)  #  await

    async def run(self):
        # async with ClientSession() as session, session.ws_connect(self.url) as ws:
        #     self.ws = ws

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