# telegram_bot.py
import os
import sys
import django
import logging

# Добавляем путь к корневой папке проекта, чтобы Python мог найти настройки Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Устанавливаем переменные окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
django.setup()

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
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
        [KeyboardButton('/catalog'), KeyboardButton('/status')],
        [KeyboardButton('/help'), KeyboardButton('/register')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать в Flower Delivery Bot!\n"
        "Вы можете заказать цветы и проверить статус своих заказов.",
        reply_markup=reply_markup
    )

# Обработчик команды /catalog для отображения доступных товаров
async def send_catalog(update: Update, context: CallbackContext) -> None:
    products = await sync_to_async(list)(Product.objects.all())  # Преобразуем в список с помощью sync_to_async
    if products:
        catalog_message = "Доступные цветы:\n"
        for product in products:
            catalog_message += f"{product.name} - {product.price} руб.\n"
        await update.message.reply_text(catalog_message)
    else:
        await update.message.reply_text("К сожалению, в данный момент товары недоступны.")


# Обработчик команды /status
async def check_status(update: Update, context: CallbackContext) -> None:
    user = await sync_to_async(lambda: User.objects.filter(username=update.message.from_user.username).first())()
    if user:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).order_by('-created_at')))()
        if orders:
            message = "Ваши заказы:\n"
            for order in orders:
                items = await sync_to_async(lambda: list(order.items.all()))()

                # Получение информации о продуктах асинхронно
                products = await sync_to_async(
                    lambda: ", ".join([f"{item.product.name} x{item.quantity}" for item in items])
                )()

                status = order.get_status_display()
                message += f"Заказ {order.id}: {products} - Статус: {status}\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("У вас нет активных заказов.")
    else:
        await update.message.reply_text(
            "Вы не зарегистрированы в системе. Пожалуйста, сначала сделайте заказ, чтобы создать учетную запись.")


# Обработчик команды /register
async def register_user(update: Update, context: CallbackContext) -> None:
    user, created = await sync_to_async(User.objects.get_or_create)(username=update.message.from_user.username)
    if created:
        await update.message.reply_text("Вы успешно зарегистрированы. Теперь вы можете делать заказы.")
    else:
        await update.message.reply_text("У вас уже есть учетная запись. Вы можете продолжить делать заказы.")

# Обновление обработчика заказов с улучшенной обработкой ошибок
async def handle_order(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    try:
        product_name, quantity = user_text.split(',')
        product = await sync_to_async(lambda: Product.objects.filter(name__iexact=product_name.strip()).first())()
        if product:
            telegram_user = update.message.from_user

            # Генерируем уникальный username, если он не предоставлен Telegram
            username = telegram_user.username or f"user_{telegram_user.id}"

            # Попробуем найти или создать пользователя с этим `username`
            user, created = await sync_to_async(User.objects.get_or_create)(
                username=username,
                defaults={'first_name': telegram_user.first_name or "User"}
            )

            if created:
                # Присваиваем Telegram ID профилю пользователя, если он еще не установлен
                profile = user.profile
                profile.telegram_chat_id = update.message.chat_id
                await sync_to_async(profile.save)()

            # Создание заказа
            order = await sync_to_async(Order.objects.create)(
                user=user, status='pending'
            )
            await sync_to_async(OrderItem.objects.create)(
                order=order, product=product, quantity=int(quantity.strip())
            )
            await update.message.reply_text(f"Ваш заказ на {quantity}x {product.name} успешно оформлен.")
        else:
            await update.message.reply_text("Товар не найден. Пожалуйста, проверьте название товара.")
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, используйте формат: Название товара, количество (например, Роза, 2).")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при оформлении заказа. Попробуйте еще раз позже.")
        print(f"Ошибка при обработке заказа: {e}")

# Обработчик команды /help
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "/start - Начать работу с ботом\n"
        "/catalog - Просмотреть каталог цветов\n"
        "/status - Проверить статус заказов\n"
        "/register - Зарегистрироваться в системе\n"
        "Чтобы заказать, отправьте сообщение в формате: Название товара, количество"
    )

# Настройка команд и обработчиков
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("catalog", send_catalog))
    application.add_handler(CommandHandler("status", check_status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register", register_user))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order))

    application.run_polling()

if __name__ == "__main__":
    setup_bot()