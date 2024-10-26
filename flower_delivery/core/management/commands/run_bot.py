# core/management/commands/run_bot.py
from django.core.management.base import BaseCommand
from telegram_bot import setup_bot

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **kwargs):
        setup_bot()
