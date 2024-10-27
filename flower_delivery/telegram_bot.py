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
        return ConversationHandler.END

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

# Обработчик для других кнопок
async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    logger.info(f"Получен запрос кнопки: {query.data} от пользователя {query.from_user.id}")

    if query.data == 'catalog':
        await send_catalog(update, context, from_callback=True)
    elif query.data == 'status':
        await check_status(update, context, from_callback=True)
    elif query.data == 'help':
        await help_command(update, context, from_callback=True)
    elif query.data == 'register':
        await register_user(update, context, from_callback=True)
    elif query.data == 'manage_orders':
        await manage_orders(update, context)
    elif query.data.startswith('order_'):
        await order_status_handler(update, context)
    elif query.data.startswith('status_'):
        await set_order_status(update, context)
    else:
        logger.warning(f"Неизвестная команда: {query.data}")

# Реализация функции управления заказами для администратора
async def manage_orders(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_chat_id = query.message.chat_id
    await query.answer()
    logger.info(f"Пользователь {user_chat_id} запросил управление заказами.")

    if str(user_chat_id) != str(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=user_chat_id, text="У вас нет прав для использования этой команды.")
        return

    orders = await sync_to_async(lambda: list(Order.objects.all().order_by('-created_at')))()
    if not orders:
        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_CHAT_ID, text="Нет активных заказов для управления.")
        return

    keyboard = []
    for order in orders:
        user = await sync_to_async(lambda: order.user.username if order.user else "Неизвестный пользователь")()
        order_text = f"Заказ {order.id}: {user} - Статус: {order.get_status_display()}"
        keyboard.append([InlineKeyboardButton(order_text, callback_data=f"order_{order.id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=ADMIN_TELEGRAM_CHAT_ID, text="Выберите заказ для изменения статуса:",
                                   reply_markup=reply_markup)

# Обработчик для выбора заказа администратором
async def order_status_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user_chat_id = query.message.chat_id
    logger.info(f"Пользователь {user_chat_id} пытается изменить статус заказа.")

    if str(user_chat_id) != str(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=user_chat_id, text="У вас нет прав для использования этой команды.")
        return

    order_id = int(query.data.split("_")[1])
    order = await sync_to_async(Order.objects.get)(id=order_id)

    keyboard = [
        [InlineKeyboardButton("В обработке", callback_data=f"status_{order.id}_processing")],
        [InlineKeyboardButton("Доставляется", callback_data=f"status_{order.id}_delivering")],
        [InlineKeyboardButton("Завершен", callback_data=f"status_{order.id}_completed")],
        [InlineKeyboardButton("Отменен", callback_data=f"status_{order.id}_canceled")]
    ]
    await query.edit_message_text(
        text=f"Выберите новый статус для заказа {order.id}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик для установки нового статуса заказа
async def set_order_status(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    logger.info(f"Пользователь {query.message.chat_id} пытается установить новый статус.")

    if str(query.message.chat_id) != str(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=query.message.chat_id, text="У вас нет прав для использования этой команды.")
        return

    data = query.data.split("_")
    order_id = int(data[1])
    new_status_key = data[2]

    status_mapping = {
        "processing": "pending",
        "delivering": "shipped",
        "completed": "delivered",
        "canceled": "canceled"
    }

    if new_status_key not in status_mapping:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Некорректный статус.")
        return

    order = await sync_to_async(Order.objects.get)(id=order_id)
    order.status = status_mapping[new_status_key]
    await sync_to_async(order.save)()
    logger.info(f"Заказ {order.id} изменен на статус {order.get_status_display()}")
    await query.edit_message_text(text=f"Статус заказа {order.id} изменен на '{order.get_status_display()}'.")

# Реализация функции отправки каталога
async def send_catalog(update: Update, context: CallbackContext, from_callback=False) -> None:
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    products = await sync_to_async(list)(Product.objects.all())
    if products:
        for product in products:
            product_description = f"{product.name}\n{product.description}\nЦена: {product.price} руб."

            if product.image:
                try:
                    product_image_url = f"{settings.DOMAIN_NAME}{product.image.url}"
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=product_image_url,
                        caption=product_description
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке изображения через URL: {e}")
                    try:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=open(product.image.path, 'rb'),
                            caption=product_description
                        )
                    except Exception as local_error:
                        logger.error(f"Ошибка при отправке локального изображения: {local_error}")
                        await context.bot.send_message(chat_id=chat_id, text=product_description)
            else:
                await context.bot.send_message(chat_id=chat_id, text=product_description)
    else:
        await context.bot.send_message(chat_id=chat_id, text="К сожалению, в данный момент товары недоступны.")

# Реализация функции проверки статуса заказа
async def check_status(update: Update, context: CallbackContext, from_callback=False) -> None:
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id
    user = await sync_to_async(lambda: User.objects.filter(username=update.effective_user.username).first())()
    if user:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user)))()
        if orders:
            response = "Ваши заказы:\n"
            for order in orders:
                response += f"Заказ #{order.id}: Статус - {order.get_status_display()}\n"
            await context.bot.send_message(chat_id=chat_id, text=response)
        else:
            await context.bot.send_message(chat_id=chat_id, text="У вас нет активных заказов.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Пользователь не найден в системе. Пожалуйста, зарегистрируйтесь.")

# Реализация функции помощи
async def help_command(update: Update, context: CallbackContext, from_callback=False) -> None:
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "/start - Начать работу с ботом\n"
            "/catalog - Просмотреть каталог цветов\n"
            "/status - Проверить статус заказов\n"
            "/register - Зарегистрироваться в системе\n"
            "Чтобы заказать, нажмите 'Заказать' и следуйте инструкциям."
        )
    )

# Реализация функции регистрации пользователя
async def register_user(update: Update, context: CallbackContext, from_callback=False) -> None:
    telegram_user = update.callback_query.from_user if from_callback else update.message.from_user
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    user, created = await sync_to_async(User.objects.get_or_create)(username=telegram_user.username)

    if created:
        await context.bot.send_message(chat_id=chat_id,
                                       text="Вы успешно зарегистрированы. Теперь вы можете делать заказы.")
    else:
        await context.bot.send_message(chat_id=chat_id,
                                       text="У вас уже есть учетная запись. Вы можете продолжить делать заказы.")

def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
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
        per_chat=True  # Изменено с per_message на per_chat
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == "__main__":
    setup_bot()
