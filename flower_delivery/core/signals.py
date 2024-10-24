from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from telegram import Bot
from django.conf import settings
from .utils import send_telegram_message

# Отправка уведомления администратору о создании нового заказа
@receiver(post_save)
def notify_admin_order_created(sender, instance, created, **kwargs):
    Order = apps.get_model('core', 'Order')
    if isinstance(instance, Order) and created:
        message = f"Новый заказ создан: #{instance.id} пользователем {instance.user.username}."
        send_telegram_message(settings.ADMIN_TELEGRAM_CHAT_ID, message)

# Отправка обновления статуса заказа пользователю через Telegram
@receiver(post_save)
def send_order_status_update(sender, instance, **kwargs):
    Order = apps.get_model('core', 'Order')
    if isinstance(instance, Order):
        if settings.TELEGRAM_BOT_TOKEN:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            user = instance.user
            status = instance.get_status_display()

            if hasattr(user, 'profile') and user.profile.telegram_chat_id:
                chat_id = user.profile.telegram_chat_id
                message = f"Ваш заказ #{instance.id} обновлен. Новый статус: {status}."
                bot.send_message(chat_id=chat_id, text=message)
            else:
                print("Telegram chat ID не найден у пользователя.")
        else:
            print("Telegram Bot Token отсутствует.")
