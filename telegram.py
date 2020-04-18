from aiogram.bot.bot import Bot

from utils import timer


class TelegramClient(Bot):
    def __init__(self, opc, token, chat_id, tor=None):
        if tor is not None:
            proxy = f"socks5h://{tor.ip}:{tor.port}"
        else:
            proxy = None

        super().__init__(token=token, proxy=proxy, timeout=10)

        self.opc = opc
        self.queue_alarms = dict()
        self.chat_id = chat_id

    @timer(5)
    async def update(self):
        # updates = await self.get_updates()
        values = "response\n"
        if self.opc:
            for cooler in self.opc.coolers:
                text = f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}"
                values.append(text)

                if cooler.Alarm:
                    if cooler not in self.queue_alarms:
                        self.queue_alarms[cooler] = {"is_sended": False, 
                            "alarm_text": f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}"} 
                else:
                    if cooler in self.queue_alarms:
                        if self.queue_alarms[cooler]["is_sended"]:
                            del self.queue_alarms[cooler]
                        
        # for cooler in self.queue_alarms:
        #     if not self.queue_alarms[cooler]["is_sended"]:
        #         await self.send_message(chat_id=self.chat_id,
        #                                 text=self.queue_alarms[cooler]["alarm_text"])
        #         self.queue_alarms[cooler]["is_sended"] = True

        # for update in updates:
        #     await update.message.answer(text="\n".join(values))            

    def start(self, loop):
        return (
            loop.create_task(self.update()),
        )
