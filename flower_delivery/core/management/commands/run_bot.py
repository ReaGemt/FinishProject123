import logging
from django.core.management.base import BaseCommand
from telegram_bot import setup_bot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Запуск Telegram бота...'))
        try:
            setup_bot()
            self.stdout.write(self.style.SUCCESS('Telegram бот успешно запущен.'))
        except Exception as e:
            logger.error(f"Ошибка при запуске Telegram бота: {e}")
            self.stdout.write(self.style.ERROR(f'Ошибка при запуске Telegram бота: {e}'))
