import os
import sys
import django
import logging
from datetime import datetime

# Добавляем путь к корневой папке проекта, чтобы Python мог найти настройки Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
django.setup()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackContext, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from core.models import Product, Order, OrderItem, User
from django.conf import settings
from asgiref.sync import sync_to_async

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_logs.log")
    ]
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECT_PRODUCT, SELECT_QUANTITY, ASKING_CUSTOM_QUANTITY, ASKING_ADDRESS, ORDER_CONFIRMATION = range(5)

# Рабочее время
WORKING_HOURS_START = 9
WORKING_HOURS_END = 18

# Загружаем токен из переменных окружения через настройки Django
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(5).write_timeout(5).build()

# Функция проверки рабочего времени
def is_within_working_hours() -> bool:
    now = datetime.now().time()
    return WORKING_HOURS_START <= now.hour < WORKING_HOURS_END

# Унифицированная функция отправки сообщений с клавиатурой
async def send_message_with_keyboard(chat_id, text, keyboard, context):
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

# Функция запуска бота
async def start(update: Update, context: CallbackContext) -> None:
    logger.info(f"Команда /start выполнена пользователем: {update.message.from_user.username}")
    keyboard = [
        [
            InlineKeyboardButton("🌹 Каталог", callback_data='catalog'),
            InlineKeyboardButton("📦 Статус заказа", callback_data='status')
        ],
        [
            InlineKeyboardButton("ℹ️ Помощь", callback_data='help'),
            InlineKeyboardButton("📝 Регистрация", callback_data='register')
        ],
        [InlineKeyboardButton("🛍 Заказать", callback_data='order')]
    ]
    if update.message.chat_id == int(ADMIN_TELEGRAM_CHAT_ID):
        keyboard.append([InlineKeyboardButton("🛠 Управление заказами", callback_data='manage_orders')])
    await send_message_with_keyboard(
        update.message.chat_id,
        "Добро пожаловать в Flower Delivery Bot!\nВыберите один из вариантов ниже:",
        keyboard,
        context
    )

async def start_order(update: Update, context: CallbackContext) -> int:
    """Начало процесса заказа с проверкой рабочего времени."""
    logger.info("Начало процесса заказа.")
    query = update.callback_query
    await query.answer()

    if not is_within_working_hours():
        await query.message.reply_text(
            "Заказы принимаются только в рабочее время (с 9:00 до 18:00).\n"
            "Заказы, присланные в нерабочее время, будут обработаны на следующий рабочий день."
        )

    products = await sync_to_async(list)(Product.objects.all())
    if products:
        keyboard = [
            [InlineKeyboardButton(product.name, callback_data=f"product_{product.id}")]
            for product in products
        ]
        await query.message.reply_text("Выберите товар для заказа:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_PRODUCT
    else:
        await query.message.reply_text("К сожалению, в данный момент товары недоступны.")
        return ConversationHandler.END

# Обработчик для выбора продукта
async def handle_product_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    try:
        await query.answer()
        product_id = int(query.data.split("_")[1])
        product = await sync_to_async(Product.objects.get)(id=product_id)
        context.user_data['product'] = product

        keyboard = [
            [InlineKeyboardButton("1", callback_data="quantity_1"),
             InlineKeyboardButton("5", callback_data="quantity_5"),
             InlineKeyboardButton("10", callback_data="quantity_10")],
            [InlineKeyboardButton("20", callback_data="quantity_20"),
             InlineKeyboardButton("50", callback_data="quantity_50")],
            [InlineKeyboardButton("Ввести количество вручную", callback_data="custom_quantity")]
        ]
        await query.edit_message_text(
            text=f"Вы выбрали: {product.name}. Выберите количество:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_QUANTITY
    except Exception as e:
        logger.error(f"Ошибка при выборе продукта: {e}")
        await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        return ConversationHandler.END

# Обработчик для выбора количества
async def handle_quantity_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    quantity = int(query.data.split("_")[1])
    context.user_data['quantity'] = quantity

    product = context.user_data.get('product')
    logger.info(f"Пользователь выбрал количество: {quantity}")

    await query.message.reply_text(
        f"Вы выбрали: {product.name}\nКоличество: {quantity}\n"
        "Пожалуйста, укажите адрес для доставки:"
    )
    return ASKING_ADDRESS

# Обработчик для ручного ввода количества
async def handle_custom_quantity(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Пожалуйста, введите желаемое количество товара:")
    return ASKING_CUSTOM_QUANTITY

async def ask_custom_quantity(update: Update, context: CallbackContext) -> int:
    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным числом.")
        context.user_data['quantity'] = quantity

        product = context.user_data.get('product')
        await update.message.reply_text(
            f"Вы выбрали: {product.name}\nКоличество: {quantity}\n"
            "Пожалуйста, укажите адрес для доставки:"
        )
        return ASKING_ADDRESS
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное положительное число для количества.")
        return ASKING_CUSTOM_QUANTITY

async def process_address_input(update: Update, context: CallbackContext) -> int:
    address = update.message.text
    context.user_data['address'] = address
    product = context.user_data.get('product')
    quantity = context.user_data.get('quantity')

    order_summary = (
        f"Вы собираетесь заказать {product.name} (x{quantity}).\n"
        f"Адрес доставки: {address}\n\nПодтвердите ваш заказ:"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_order')],
        [InlineKeyboardButton("❌ Отменить", callback_data='cancel_order')]
    ]
    await update.message.reply_text(order_summary, reply_markup=InlineKeyboardMarkup(keyboard))
    return ORDER_CONFIRMATION

async def confirm_order(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    product = context.user_data.get('product')
    quantity = context.user_data.get('quantity')
    address = context.user_data.get('address')

    user, _ = await sync_to_async(User.objects.get_or_create)(username=query.from_user.username)
    order = await sync_to_async(Order.objects.create)(user=user, address=address)
    await sync_to_async(OrderItem.objects.create)(order=order, product=product, quantity=quantity)

    await query.edit_message_text(text=f"Ваш заказ на '{product.name}' в количестве {quantity} успешно создан!")
    return ConversationHandler.END

async def cancel_order(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    logger.info("Пользователь отменил заказ.")
    await query.edit_message_text(text="Ваш заказ был отменен.")
    return ConversationHandler.END

def setup_bot(button_handler=None):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_order, pattern='^order$')],
        states={
            SELECT_PRODUCT: [CallbackQueryHandler(handle_product_selection, pattern='^product_')],
            SELECT_QUANTITY: [
                CallbackQueryHandler(handle_quantity_selection, pattern='^quantity_'),
                CallbackQueryHandler(handle_custom_quantity, pattern='^custom_quantity$')
            ],
            ASKING_CUSTOM_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_custom_quantity)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_address_input)],
            ORDER_CONFIRMATION: [
                CallbackQueryHandler(confirm_order, pattern='^confirm_order$'),
                CallbackQueryHandler(cancel_order, pattern='^cancel_order$')
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_order, pattern='^cancel_order$')],
        per_chat=True
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == "__main__":
    setup_bot()
