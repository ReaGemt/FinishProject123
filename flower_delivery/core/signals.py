from telegram import Bot
from django.conf import settings
from .models import Order, UserProfile  # Обновлено с правильным именем модели
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .utils import send_telegram_message

logger = logging.getLogger(__name__)

# Отправка уведомления администратору о создании нового заказа
@receiver(post_save, sender=Order)
def notify_admin_order_created(sender, instance, created, **kwargs):
    if created:
        message = f"Новый заказ создан: #{instance.id} пользователем {instance.user.username}."
        try:
            send_telegram_message(settings.ADMIN_TELEGRAM_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администратору: {e}")

# Отправка обновления статуса заказа пользователю через Telegram
@receiver(post_save, sender=Order)
def send_order_status_update(sender, instance, **kwargs):
    if settings.TELEGRAM_BOT_TOKEN:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        user = instance.user
        status = instance.get_status_display()

        if hasattr(user, 'profile') and user.profile.telegram_chat_id:
            chat_id = user.profile.telegram_chat_id
            message = f"Ваш заказ #{instance.id} обновлен. Новый статус: {status}."
            try:
                bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
        else:
            logger.warning("Telegram chat ID не найден у пользователя.")
    else:
        logger.warning("Telegram Bot Token отсутствует.")

# Создание профиля пользователя при создании нового пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# Сохранение профиля пользователя
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
