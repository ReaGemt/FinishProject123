# core/management/commands/generate_reports.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Order, Report
from django.db.models import Sum, F

class Command(BaseCommand):
    help = 'Генерирует ежедневный отчет по продажам'

    def handle(self, *args, **options):
        today = timezone.now().date()
        orders = Order.objects.filter(
            created_at__date=today,
            status='delivered'
        )

        total_sales = orders.aggregate(
            total=Sum(F('items__quantity') * F('items__product__price'))
        )['total'] or 0

        total_orders = orders.count()
        total_customers = orders.values('user').distinct().count()

        Report.objects.create(
            total_sales=total_sales,
            total_orders=total_orders,
            total_customers=total_customers
        )

        self.stdout.write(self.style.SUCCESS(f'Отчет за {today} создан'))
