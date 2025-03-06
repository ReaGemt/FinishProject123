import os
import sys
import django
import logging
from datetime import datetime

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_logs.log")
    ]
)
logger = logging.getLogger(__name__)

SELECT_PRODUCT, SELECT_QUANTITY, ASKING_CUSTOM_QUANTITY, ASKING_ADDRESS, ORDER_CONFIRMATION = range(5)
WORKING_HOURS_START = 9
WORKING_HOURS_END = 18

TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(5).write_timeout(5).build()

def is_within_working_hours() -> bool:
    now = datetime.now().time()
    return WORKING_HOURS_START <= now.hour < WORKING_HOURS_END

async def send_message_with_keyboard(chat_id, text, keyboard, context):
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

async def notify_admin(order):
    if ADMIN_TELEGRAM_CHAT_ID:
        text = (f"📢 Новый заказ!\n\n"
                f"Пользователь: {order.user.username}\n"
                f"Товары: {', '.join([f'{item.product.name} x{item.quantity}' for item in order.orderitem_set.all()])}\n"
                f"Адрес: {order.address}")
        await application.bot.send_message(chat_id=ADMIN_TELEGRAM_CHAT_ID, text=text)

async def start(update: Update, context: CallbackContext) -> None:
    logger.info(f"Команда /start выполнена пользователем: {update.message.from_user.username}")
    keyboard = [
        [InlineKeyboardButton("🌸 Каталог", callback_data='catalog'),
         InlineKeyboardButton("📦 Статус заказа", callback_data='status')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help'),
         InlineKeyboardButton("📝 История заказов", callback_data='order_history')],
        [InlineKeyboardButton("🛒 Заказать", callback_data='order')]
    ]
    if update.message.chat_id == int(ADMIN_TELEGRAM_CHAT_ID):
        keyboard.append([InlineKeyboardButton("🔧 Управление заказами", callback_data='manage_orders')])
    await send_message_with_keyboard(
        update.message.chat_id,
        "Добро пожаловать в Flower Delivery Bot!\nВыберите один из вариантов ниже:",
        keyboard,
        context
    )

async def order_history(update: Update, context: CallbackContext) -> None:
    user, _ = await sync_to_async(User.objects.get_or_create)(username=update.message.from_user.username)
    orders = await sync_to_async(list)(Order.objects.filter(user=user))
    if not orders:
        await update.message.reply_text("У вас нет предыдущих заказов.")
        return

    history_text = "📜 Ваша история заказов:\n"
    for order in orders:
        history_text += (f"\n🛍️ Заказ #{order.id} - {order.get_status_display()}\n"
                         f"Товары: {', '.join([f'{item.product.name} x{item.quantity}' for item in order.orderitem_set.all()])}\n"
                         f"Адрес: {order.address}\n"
                         f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}")
    await update.message.reply_text(history_text)

async def confirm_order(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    product = context.user_data.get('product')
    quantity = context.user_data.get('quantity')
    address = context.user_data.get('address')

    user, _ = await sync_to_async(User.objects.get_or_create)(username=query.from_user.username)
    order = await sync_to_async(Order.objects.create)(user=user, address=address)
    await sync_to_async(OrderItem.objects.create)(order=order, product=product, quantity=quantity)
    
    await notify_admin(order)

    await query.edit_message_text(text=f"Ваш заказ на '{product.name}' в количестве {quantity} успешно создан!")
    return ConversationHandler.END

def setup_bot():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("order_history", order_history))
    application.run_polling()

if __name__ == "__main__":
    setup_bot()