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
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем токен из переменных окружения через настройки Django
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")# Добавьте ваш ID администратора
print(ADMIN_TELEGRAM_CHAT_ID)
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
    # Добавляем кнопку управления заказами только для администратора
    if update.message.chat_id == int(ADMIN_TELEGRAM_CHAT_ID):
        keyboard.append([InlineKeyboardButton("🛠 Управление заказами", callback_data='manage_orders')])
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
    elif query.data == 'manage_orders':
        await manage_orders(update, context)
    elif query.data.startswith('order_'):
        await order_status_handler(update, context)
    elif query.data.startswith('status_'):
        await set_order_status(update, context)

# Обработчик команды /help
async def help_command(update: Update, context: CallbackContext, from_callback=False) -> None:
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "/start - Начать работу с ботом\n"
            "/catalog - Просмотреть каталог цветов\n"
            "/status - Проверить статус заказов\n"
            "/register - Зарегистрироваться в системе\n"
            "/manage_orders - Управление заказами (для администраторов)\n"
            "Чтобы заказать, отправьте сообщение в формате: Название товара, количество"
        )
    )


# Обработчик команды /register
async def register_user(update: Update, context: CallbackContext, from_callback=False) -> None:
    telegram_user = update.callback_query.from_user if from_callback else update.message.from_user
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    user, created = await sync_to_async(User.objects.get_or_create)(username=telegram_user.username)

    # Обновляем или сохраняем telegram_chat_id в профиле пользователя
    if created or not hasattr(user, 'profile') or not user.profile.telegram_chat_id:
        profile, _ = await sync_to_async(UserProfile.objects.get_or_create)(user=user)
        profile.telegram_chat_id = chat_id
        await sync_to_async(profile.save)()

    if created:
        await context.bot.send_message(chat_id=chat_id,
                                       text="Вы успешно зарегистрированы. Теперь вы можете делать заказы.")
    else:
        await context.bot.send_message(chat_id=chat_id,
                                       text="У вас уже есть учетная запись. Вы можете продолжить делать заказы.")
# Обработчик команды /manage_orders для администратора
async def manage_orders(update: Update, context: CallbackContext) -> None:
    user_chat_id = update.callback_query.message.chat_id
    if str(user_chat_id) != str(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=user_chat_id, text="У вас нет прав для использования этой команды.")
        return

    orders = await sync_to_async(lambda: list(Order.objects.all().order_by('-created_at')))()
    if not orders:
        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_CHAT_ID, text="Нет активных заказов для управления.")
        return

    keyboard = []
    for order in orders:
        # Заменим синхронный доступ к пользователю на асинхронный
        user = await sync_to_async(lambda: order.user.username if order.user else "Неизвестный пользователь")()
        order_text = f"Заказ {order.id}: {user} - Статус: {order.get_status_display()}"
        keyboard.append([InlineKeyboardButton(order_text, callback_data=f"order_{order.id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=ADMIN_TELEGRAM_CHAT_ID, text="Выберите заказ для изменения статуса:", reply_markup=reply_markup)

# Обработчик изменения статуса заказа
# Обработчик изменения статуса заказа
async def order_status_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_chat_id = query.message.chat_id

    if str(user_chat_id) != str(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=user_chat_id, text="У вас нет прав для использования этой команды.")
        return

    order_id = int(query.data.split("_")[1])
    order = await sync_to_async(Order.objects.get)(id=order_id)

    # Создаем кнопки для изменения статуса
    keyboard = [
        [InlineKeyboardButton("В обработке", callback_data=f"status_{order.id}_processing")],
        [InlineKeyboardButton("Доставляется", callback_data=f"status_{order.id}_delivering")],
        [InlineKeyboardButton("Завершен", callback_data=f"status_{order.id}_completed")],
        [InlineKeyboardButton("Отменен", callback_data=f"status_{order.id}_canceled")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Выберите новый статус для заказа {order.id}:", reply_markup=reply_markup)

# Обработчик установки нового статуса заказа
# Обработчик установки нового статуса заказа
async def set_order_status(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # Добавьте вывод для отладки
    print(f"ADMIN_TELEGRAM_CHAT_ID: {ADMIN_TELEGRAM_CHAT_ID}, query.message.chat_id: {query.message.chat_id}")

    if int(query.message.chat_id) != int(ADMIN_TELEGRAM_CHAT_ID):
        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text="У вас нет прав для использования этой команды.")
        return

    data = query.data.split("_")
    order_id = int(data[1])
    new_status_key = data[2]

    # Используем ключи для сохранения статусов
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
    order.status = status_mapping[new_status_key]  # Сохраняем ключ вместо значения
    await sync_to_async(order.save)()

    await query.edit_message_text(text=f"Статус заказа {order.id} изменен на '{order.get_status_display()}'.")


# Обработчик команды /catalog для отображения доступных товаров
async def send_catalog(update: Update, context: CallbackContext, from_callback=False) -> None:
    chat_id = update.callback_query.message.chat_id if from_callback else update.message.chat_id

    products = await sync_to_async(list)(Product.objects.all())
    if products:
        for product in products:
            # Формируем описание для каждого товара
            product_description = f"{product.name}\n{product.description}\nЦена: {product.price} руб."

            # Проверяем, есть ли изображение у продукта и отправляем сообщение с фото
            if product.image:
                product_image_url = f"{settings.DOMAIN_NAME}{product.image.url}"

                # Попробуем использовать локальный файл, если URL не работает
                try:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=product_image_url,
                        caption=product_description
                    )
                except Exception as e:
                    logger.error(f"Ошибка при загрузке изображения через URL. Попытка использовать локальный файл: {e}")
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
                # Если нет изображения, просто отправляем текстовое сообщение
                await context.bot.send_message(chat_id=chat_id, text=product_description)
    else:
        await context.bot.send_message(chat_id=chat_id, text="К сожалению, в данный момент товары недоступны.")


# Обработчик команды /status
async def check_status(update: Update, context: CallbackContext, from_callback=False) -> None:
    telegram_user = update.callback_query.from_user if from_callback else update.message.from_user

    user = await sync_to_async(User.objects.filter(username=telegram_user.username).first)()
    if user:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).order_by('-created_at')))()
        if orders:
            message = "Ваши заказы:\n"
            for order in orders:
                items = await sync_to_async(lambda: list(order.items.all()))()
                product_info = await sync_to_async(lambda: ", ".join([f"{item.product.name} x{item.quantity}" for item in items]))()
                status = order.get_status_display()
                message += f"Заказ {order.id}: {product_info} - Статус: {status}\n"
            await context.bot.send_message(chat_id=telegram_user.id, text=message)
        else:
            await context.bot.send_message(chat_id=telegram_user.id, text="У вас нет активных заказов.")
    else:
        await context.bot.send_message(
            chat_id=telegram_user.id,
            text="Вы не зарегистрированы в системе. Пожалуйста, сначала сделайте заказ, чтобы создать учетную запись."
        )

# Обработчик сообщений для создания заказа
async def handle_order_message(update: Update, context: CallbackContext) -> None:
    try:
        if not is_within_working_hours():
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="К сожалению, заказы принимаются только с 9:00 до 18:00 с Понедельника по Воскресенье."
            )
            return

        # Оставшаяся логика обработки заказа
        message_text = update.message.text
        chat_id = update.message.chat_id

        # Разбираем сообщение пользователя
        try:
            product_name, quantity = message_text.split(',')
            quantity = int(quantity.strip())
        except ValueError:
            await context.bot.send_message(chat_id=chat_id,
                                           text="Пожалуйста, укажите товар и количество в формате: Название товара, количество.")
            return

        # Поиск продукта по имени
        product = await sync_to_async(Product.objects.filter)(name__icontains=product_name.strip())
        if not await sync_to_async(product.exists)():
            await context.bot.send_message(chat_id=chat_id, text=f"Товар '{product_name}' не найден.")
            return

        # Создание нового заказа
        product = await sync_to_async(product.first)()
        user, created = await sync_to_async(User.objects.get_or_create)(username=update.message.from_user.username)

        # Создание заказа и добавление элемента заказа
        order = await sync_to_async(Order.objects.create)(user=user, address="Адрес не указан")
        await sync_to_async(OrderItem.objects.create)(order=order, product=product, quantity=quantity)

        await context.bot.send_message(chat_id=chat_id,
                                       text=f"Ваш заказ на '{product.name}' в количестве {quantity} успешно создан!")
    except Exception as e:
        logger.error(f"Ошибка при обработке заказа: {e}")
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text="Произошла ошибка при создании заказа. Пожалуйста, попробуйте еще раз.")

def is_within_working_hours():
    now = datetime.now()
    if now.weekday() not in settings.WORKING_DAYS:
        return False
    if now.hour < settings.WORKING_HOURS_START or now.hour >= settings.WORKING_HOURS_END:
        return False
    return True

# Настройка бота
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_message))
    application.run_polling()

if __name__ == "__main__":
    setup_bot()
