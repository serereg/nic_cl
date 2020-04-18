from aiogram.bot.bot import Bot

from utils import timer


class TelegramClient(Bot):
    def __init__(self, opc, token, chat_id, tor=None):
        if tor is not None:
            proxy = f"socks5h://{tor.host}:{tor.port}"
        else:
            proxy = None

        super().__init__(token=token, proxy=proxy, timeout=10)

        self.opc = opc
        self.alarms = set()
        self.chat_id = chat_id

    @timer(5)
    async def update(self):
        updates = await self.get_updates()

        values = []
        for cooler in self.opc.coolers:
            text = f"{cooler.name}, T={cooler.pv.Value:.1f}, SP={cooler.sp:.1f}"
            values.append(text)
            if cooler.Alarm and cooler not in self.alarms:
                await self.send_message(chat_id=self.chat_id, text=text)
            self.alarms.add(cooler) if cooler.Alarm else self.alarms.remove(cooler)

        for update in updates:
            await update.message.answer(text="\n".join(values))            

    async def start(self, loop):
        return (
            loop.create_task(self.update()),
        )
