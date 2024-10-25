import logging
import os
import sys

import django
from asgiref.sync import sync_to_async
from django.conf import settings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

from core.models import Product, Order, User

# Добавляем путь к корневой папке проекта, чтобы Python мог найти настройки Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
django.setup()

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Загружаем токен из переменных окружения через настройки Django
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# Обработчик команды /start с добавлением интерактивного меню
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("🌹 Каталог", callback_data='catalog'), InlineKeyboardButton("📦 Статус заказа", callback_data='status')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help'), InlineKeyboardButton("📝 Регистрация", callback_data='register')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Добро пожаловать в Flower Delivery Bot!\nВыберите один из вариантов ниже:",
        reply_markup=reply_markup
    )

# Обработчик нажатий Inline-кнопок
async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    handlers = {
        'catalog': send_catalog,
        'status': check_status,
        'help': help_command,
        'register': register_user
    }
    handler = handlers.get(query.data)
    if handler:
        await handler(update, context, from_callback=True)

# Настройка бота
def setup_bot():
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при настройке бота: {e}")

# Обработчик команды /catalog для отображения доступных товаров
async def send_catalog(update: Update, context: CallbackContext, from_callback=False) -> None:
    try:
        chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id
        products = await sync_to_async(list)()
        if products:
            catalog_message = "Доступные цветы:\n" + "\n".join(f"{product.name} - {product.price} руб." for product in products)
        else:
            catalog_message = "К сожалению, в данный момент товары недоступны."
        await context.bot.send_message(chat_id=chat_id, text=catalog_message)
    except Exception as e:
        logger.error(f"Ошибка при отправке каталога: {e}")

# Обработчик команды /status
async def check_status(update: Update, context: CallbackContext, from_callback=False) -> None:
    try:
        telegram_user = update.callback_query.from_user if from_callback else update.message.from_user
        user = await sync_to_async(User.objects.filter(username=telegram_user.username).first)()
        if user:
            orders = await sync_to_async(list)(Order.objects.filter(user=user).order_by('-created_at'))
            if orders:
                message = "Ваши заказы:\n" + "\n".join(
                    f"Заказ {order.id}: {', '.join(f'{item.product.name} x{item.quantity}' for item in order.items.all())} - Статус: {order.get_status_display()}"
                    for order in orders
                )
            else:
                message = "У вас нет активных заказов."
        else:
            message = "Вы не зарегистрированы в системе. Пожалуйста, сначала сделайте заказ, чтобы создать учетную запись."
        await context.bot.send_message(chat_id=telegram_user.id, text=message)
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса заказа: {e}")

# Обработчик команды /register
async def register_user(update: Update, context: CallbackContext, from_callback=False) -> None:
    try:
        telegram_user = update.callback_query.from_user if from_callback else update.message.from_user
        user, created = await sync_to_async(User.objects.get_or_create)(username=telegram_user.username)
        message = "Вы успешно зарегистрированы." if created else "У вас уже есть учетная запись."
        await context.bot.send_message(chat_id=telegram_user.id, text=message)
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")

# Обработчик команды /help
async def help_command(update: Update, context: CallbackContext, from_callback=False) -> None:
    try:
        chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "/start - Начать работу с ботом\n"
                "/catalog - Просмотреть каталог цветов\n"
                "/status - Проверить статус заказов\n"
                "/register - Зарегистрироваться в системе\n"
                "Чтобы заказать, отправьте сообщение в формате: Название товара, количество"
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке команды помощи: {e}")

if __name__ == "__main__":
    setup_bot()
