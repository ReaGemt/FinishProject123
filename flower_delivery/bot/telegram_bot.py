from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Product, Order, OrderItem, User

# Обработчик команды /start с добавлением интерактивного меню
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton('/catalog'), KeyboardButton('/status')],
        [KeyboardButton('/help')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        "Добро пожаловать в Flower Delivery Bot!\n"
        "Вы можете заказать цветы и проверить статус своих заказов.",
        reply_markup=reply_markup
    )

# Обработчик команды /status
def check_status(update: Update, context: CallbackContext) -> None:
    user = User.objects.filter(username=update.message.from_user.username).first()
    if user:
        orders = Order.objects.filter(user=user)
        if orders.exists():
            message = "Ваши заказы:\n"
            for order in orders:
                status = order.get_status_display()
                products = ", ".join([f"{item.product.name} x{item.quantity}" for item in order.orderitem_set.all()])
                message += f"Заказ {order.id}: {products} - Статус: {status}\n"
            update.message.reply_text(message)
        else:
            update.message.reply_text("У вас нет активных заказов.")
    else:
        update.message.reply_text("Вы не зарегистрированы в системе.")

# Обновление обработчика заказов с улучшенной обработкой ошибок
def handle_order(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    try:
        product_name, quantity = user_text.split(',')
        product = Product.objects.filter(name__iexact=product_name.strip()).first()
        if product:
            user, created = User.objects.get_or_create(username=update.message.from_user.username)
            order = Order.objects.create(user=user, status='pending')
            OrderItem.objects.create(order=order, product=product, quantity=int(quantity.strip()))
            update.message.reply_text(f"Ваш заказ на {quantity}x {product.name} успешно оформлен.")
        else:
            update.message.reply_text("Товар не найден. Пожалуйста, проверьте название товара.")
    except ValueError:
        update.message.reply_text("Пожалуйста, используйте формат: Название товара, количество (например, Роза, 2).")
    except Exception as e:
        update.message.reply_text("Произошла ошибка при оформлении заказа. Попробуйте еще раз позже.")

# Обработчик команды /help
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "/start - Начать работу с ботом\n"
        "/catalog - Просмотреть каталог цветов\n"
        "/status - Проверить статус заказов\n"
        "Чтобы заказать, отправьте сообщение в формате: Название товара, количество"
    )

# Настройка команд и обработчиков
def setup_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("catalog", send_catalog))
    dispatcher.add_handler(CommandHandler("status", check_status))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_order))

    updater.start_polling()
    updater.idle()
