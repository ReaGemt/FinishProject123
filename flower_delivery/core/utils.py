import asyncio
import logging
from telegram import Bot
from django.conf import settings
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Проверяем, что настройки для Telegram корректно заданы
if settings.ENABLE_TELEGRAM_NOTIFICATIONS and settings.TELEGRAM_BOT_TOKEN:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
else:
    bot = None
    logger.warning("Telegram Bot не инициализирован: отсутствует токен или уведомления отключены.")

async def async_send_message(chat_id, message):
    try:
        if bot:
            await bot.send_message(chat_id=chat_id, text=message)
        else:
            logger.warning(f"Сообщение не отправлено. Bot не инициализирован.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram (chat_id={chat_id}): {e}")

def send_telegram_message(chat_id, message):
    async_to_sync(async_send_message)(chat_id, message)
