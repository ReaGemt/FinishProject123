import asyncio
from telegram import Bot
from django.conf import settings

async def async_send_message(chat_id, message):
    try:
        if settings.ENABLE_TELEGRAM_NOTIFICATIONS:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")

def send_telegram_message(chat_id, message):
    asyncio.run(async_send_message(chat_id, message))
