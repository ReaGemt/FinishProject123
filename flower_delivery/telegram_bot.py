import os
import sys
import django
import logging

# Добавляем путь к корневой папке проекта, чтобы Python мог найти настройки Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Устанавливаем переменные окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
django.setup()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from core.models import Product, Order, OrderItem, User
from django.conf import settings
from asgiref.sync import sync_to_async

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем токен из переменных окружения через настройки Django
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# Обработчик команды /start с добавлением интерактивного меню
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🌹 Каталог", callback_data='catalog'),
            InlineKeyboardButton("📦 Статус заказа", callback_data='status')
        ],
        [
            InlineKeyboardButton("ℹ️ Помощь", callback_data='help'),
            InlineKeyboardButton("📝 Регистрация", callback_data='register')
        ]
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

    if query.data == 'catalog':
        await send_catalog(update, context, from_callback=True)
    elif query.data == 'status':
        await check_status(update, context, from_callback=True)
    elif query.data == 'help':
        await help_command(update, context, from_callback=True)
    elif query.data == 'register':
        await register_user(update, context, from_callback=True)

# Настройка бота
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

# Обработчик команды /catalog для отображения доступных товаров
async def send_catalog(update: Update, context: CallbackContext, from_callback=False) -> None:
    if from_callback:
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.message.chat_id

    products = await sync_to_async(list)(Product.objects.all())  # Преобразуем в список с помощью sync_to_async
    if products:
        catalog_message = "Доступные цветы:\n"
        for product in products:
            catalog_message += f"{product.name} - {product.price} руб.\n"
        await context.bot.send_message(chat_id=chat_id, text=catalog_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text="К сожалению, в данный момент товары недоступны.")

# Обработчик команды /status
async def check_status(update: Update, context: CallbackContext, from_callback=False) -> None:
    if from_callback:
        telegram_user = update.callback_query.from_user
    else:
        telegram_user = update.message.from_user

    user = await sync_to_async(lambda: User.objects.filter(username=telegram_user.username).first())()
    if user:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).order_by('-created_at')))()
        if orders:
            message = "Ваши заказы:\n"
            for order in orders:
                items = await sync_to_async(lambda: list(order.items.all()))()
                products = await sync_to_async(
                    lambda: ", ".join([f"{item.product.name} x{item.quantity}" for item in items])
                )()
                status = order.get_status_display()
                message += f"Заказ {order.id}: {products} - Статус: {status}\n"
            await context.bot.send_message(chat_id=telegram_user.id, text=message)
        else:
            await context.bot.send_message(chat_id=telegram_user.id, text="У вас нет активных заказов.")
    else:
        await context.bot.send_message(
            chat_id=telegram_user.id,
            text="Вы не зарегистрированы в системе. Пожалуйста, сначала сделайте заказ, чтобы создать учетную запись."
        )

# Обработчик команды /register
async def register_user(update: Update, context: CallbackContext, from_callback=False) -> None:
    if from_callback:
        telegram_user = update.callback_query.from_user
    else:
        telegram_user = update.message.from_user

    user, created = await sync_to_async(User.objects.get_or_create)(username=telegram_user.username)
    if created:
        await context.bot.send_message(chat_id=telegram_user.id, text="Вы успешно зарегистрированы. Теперь вы можете делать заказы.")
    else:
        await context.bot.send_message(chat_id=telegram_user.id, text="У вас уже есть учетная запись. Вы можете продолжить делать заказы.")

# Обработчик команды /help
async def help_command(update: Update, context: CallbackContext, from_callback=False) -> None:
    if from_callback:
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.message.chat_id

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

if __name__ == "__main__":
    setup_bot()
