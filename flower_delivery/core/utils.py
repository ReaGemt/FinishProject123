# core\utils.py
import logging
from telegram import Bot
from django.conf import settings
from asgiref.sync import async_to_sync
from .models import Order, OrderItem, Product
from datetime import datetime, timedelta
from django.utils import timezone


logger = logging.getLogger(__name__)

# Проверка и инициализация Telegram бота
def get_bot():
    if settings.ENABLE_TELEGRAM_NOTIFICATIONS and settings.TELEGRAM_BOT_TOKEN:
        return Bot(token=settings.TELEGRAM_BOT_TOKEN)
    else:
        if not settings.ENABLE_TELEGRAM_NOTIFICATIONS:
            logger.warning("Уведомления в Telegram отключены настройками.")
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Отсутствует TELEGRAM_BOT_TOKEN в настройках.")
        return None

async def async_send_message(chat_id, message):
    bot = get_bot()
    try:
        if bot:
            await bot.send_message(chat_id=chat_id, text=message)
        else:
            logger.warning(f"Сообщение не отправлено. Bot не инициализирован.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram (chat_id={chat_id}): {e}")

def send_telegram_message(chat_id, message):
    async_to_sync(async_send_message)(chat_id, message)

from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate

def generate_sales_report(start_date=None, end_date=None, days=30):
    if start_date and end_date:
        # Проверяем и преобразуем даты с учетом временной зоны
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)
        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date)
    else:
        # Используем последние 'days' дней
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

    # Фильтрация заказов
    orders = Order.objects.filter(created_at__range=(start_date, end_date), status='delivered')

    # Агрегация данных
    total_sales = orders.aggregate(
        total_sales=Sum(F('items__quantity') * F('items__product__price'))
    )['total_sales'] or 0

    total_orders = orders.count()
    total_customers = orders.values('user').distinct().count()

    # Продажи по дням
    daily_sales = orders.annotate(date=TruncDate('created_at')).values('date').annotate(
        total_sales=Sum(F('items__quantity') * F('items__product__price'))
    ).order_by('date')

    # Топ продаваемых товаров
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values('product__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:10]

    return {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'daily_sales': list(daily_sales),
        'top_products': list(top_products),
    }



def generate_sales_report_by_period(start_date=None, end_date=None, days=None):
    # Если указан конкретный период дат, используем его
    if start_date and end_date:
        orders = Order.objects.filter(created_at__range=(start_date, end_date))
    # Иначе используем последние 'days' дней
    elif days:
        end_date = timezone.now()  # Учитываем часовой пояс
        start_date = end_date - timedelta(days=days)
        orders = Order.objects.filter(created_at__range=(start_date, end_date))
    else:
        # Обработка по умолчанию - за последние 30 дней
        end_date = timezone.now()  # Учитываем часовой пояс
        start_date = end_date - timedelta(days=30)
        orders = Order.objects.filter(created_at__range=(start_date, end_date))

    # Исправление: используем метод `get_total_price()`
    total_sales = sum(order.get_total_price() for order in orders)
    total_orders = orders.count()
    total_customers = orders.values('user').distinct().count()

    return {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
    }


def generate_sales_report_by_custom_period(start_date=None, end_date=None):
    if not start_date or not end_date:
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=30)

    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        status='delivered'
    )

    total_sales = orders.aggregate(
        total_sales=Sum(F('items__quantity') * F('items__product__price'))
    )['total_sales'] or 0

    total_orders = orders.count()
    total_customers = orders.values('user').distinct().count()

    report = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
    }

    return report