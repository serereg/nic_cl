# from aiogram.bot.bot import Bot  # не поддерживает socks5h
import siotelegram

from utils import timer


# class TelegramClient(Bot):
class TelegramClient():
    def __init__(self, opc, token, chat_id, tor=None):
        if tor is not None:
            proxy = f"socks5h://{tor.ip}:{tor.port}"
        else:
            proxy = None

        # super().__init__(token=token, proxy=proxy, timeout=10)
        self.api = siotelegram.RequestsTelegramApi(token, 
            timeout=10, 
            proxy=proxy)
        self.opc = opc
        self.queue_alarms = dict()
        self.chat_id = chat_id

    @timer(5)
    async def update(self):
        # updates = await self.get_updates()
        updates = self.api.get_updates()

        values = ["response\n"]
        if self.opc:
            for cooler in self.opc.coolers:
                text = f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}\n"
                values.append(text)

                if cooler.Alarm:
                    if cooler not in self.queue_alarms:
                        self.queue_alarms[cooler] = {"is_sended": False, 
                            "alarm_text": f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}"} 
                else:
                    if cooler in self.queue_alarms:
                        if self.queue_alarms[cooler]["is_sended"]:
                            del self.queue_alarms[cooler]
                        
        for cooler in self.queue_alarms:
            if not self.queue_alarms[cooler]["is_sended"]:
                # await self.send_message(chat_id=self.chat_id,
                #    text=self.queue_alarms[cooler]["alarm_text"])
                self.api.send_message(chat_id = self.chat_id, 
                    text = self.queue_alarms[cooler]["alarm_text"])
                self.queue_alarms[cooler]["is_sended"] = True

        for update in updates["result"]:
            self.api.send_message(chat_id = self.chat_id, text = "".join(values))
            # await update.message.answer(text="\n".join(values))            

    def start(self, loop):
        return (
            loop.create_task(self.update()),
        )
