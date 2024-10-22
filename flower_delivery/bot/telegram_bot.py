import os
import sys
import django

# Добавляем путь к корневой папке проекта, чтобы Python мог найти настройки Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Устанавливаем переменные окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
django.setup()

from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from django.conf import settings
from core.models import Product, Order, OrderItem, User

# Загружаем токен из переменных окружения через настройки Django
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# Обработчик команды /start с добавлением интерактивного меню
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton('/catalog'), KeyboardButton('/status')],
        [KeyboardButton('/help')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать в Flower Delivery Bot!\n"
        "Вы можете заказать цветы и проверить статус своих заказов.",
        reply_markup=reply_markup
    )

# Обработчик команды /catalog для отображения доступных товаров
async def send_catalog(update: Update, context: CallbackContext) -> None:
    products = Product.objects.all()
    if products.exists():
        catalog_message = "Доступные цветы:\n"
        for product in products:
            catalog_message += f"{product.name} - {product.price} руб.\n"
        await update.message.reply_text(catalog_message)
    else:
        await update.message.reply_text("К сожалению, в данный момент товары недоступны.")

# Обработчик команды /status
async def check_status(update: Update, context: CallbackContext) -> None:
    user = User.objects.filter(username=update.message.from_user.username).first()
    if user:
        orders = Order.objects.filter(user=user).order_by('-created_at')
        if orders.exists():
            message = "Ваши заказы:\n"
            for order in orders:
                status = order.get_status_display()
                products = ", ".join([f"{item.product.name} x{item.quantity}" for item in order.orderitem_set.all()])
                message += f"Заказ {order.id}: {products} - Статус: {status}\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("У вас нет активных заказов.")
    else:
        await update.message.reply_text("Вы не зарегистрированы в системе. Пожалуйста, сначала сделайте заказ, чтобы создать учетную запись.")

# Обновление обработчика заказов с улучшенной обработкой ошибок
async def handle_order(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    try:
        product_name, quantity = user_text.split(',')
        product = Product.objects.filter(name__iexact=product_name.strip()).first()
        if product:
            user, created = User.objects.get_or_create(username=update.message.from_user.username)
            order = Order.objects.create(user=user, status='pending')
            OrderItem.objects.create(order=order, product=product, quantity=int(quantity.strip()))
            await update.message.reply_text(f"Ваш заказ на {quantity}x {product.name} успешно оформлен.")
        else:
            await update.message.reply_text("Товар не найден. Пожалуйста, проверьте название товара.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, используйте формат: Название товара, количество (например, Роза, 2).")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при оформлении заказа. Попробуйте еще раз позже.")

# Обработчик команды /help
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "/start - Начать работу с ботом\n"
        "/catalog - Просмотреть каталог цветов\n"
        "/status - Проверить статус заказов\n"
        "Чтобы заказать, отправьте сообщение в формате: Название товара, количество"
    )

# Настройка команд и обработчиков
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("catalog", send_catalog))
    application.add_handler(CommandHandler("status", check_status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order))

    application.run_polling()

if __name__ == "__main__":
    setup_bot()
