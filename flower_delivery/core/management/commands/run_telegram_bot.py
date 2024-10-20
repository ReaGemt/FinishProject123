from telegram_bot import setup_bot

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **kwargs):
        setup_bot()
