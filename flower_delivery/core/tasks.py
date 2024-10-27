from celery import shared_task
from django.core.mail import send_mail
from .utils import generate_sales_report_by_period

@shared_task
def send_daily_sales_report():
    report = generate_sales_report_by_period(1)
    send_mail(
        'Ежедневный отчет по продажам',
        f'Общий объем продаж: {report["total_sales"]}\n'
        f'Общее количество заказов: {report["total_orders"]}\n'
        f'Общее количество клиентов: {report["total_customers"]}',
        'info@flowerdelivery.ru',
        ['manager@flowerdelivery.ru']
    )
