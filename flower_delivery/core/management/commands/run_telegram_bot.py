# flower_delivery\system\management\commands\run_telegram_bot.py
from django.core.management.base import BaseCommand
from flower_delivery.telegram_bot import setup_bot
from telegram_bot import setup_bot
from bot.telegram_bot import setup_bot


class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **kwargs):
        setup_bot()