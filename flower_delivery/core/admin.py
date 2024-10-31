# core/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import Product, Order, Review, Report, OrderItem
from .utils import generate_sales_report

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'rating', 'is_popular', 'created_by')
    list_filter = ('category', 'is_popular', 'rating')
    search_fields = ('name',)
    verbose_name = _('Продукт')
    verbose_name_plural = _('Продукты')

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_products', 'get_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('items__product')

    def get_products(self, obj):
        links = [
            f'<a href="/admin/core/product/{item.product.id}/change/">{item.product.name}</a>'
            for item in obj.items.all()
        ]
        return mark_safe("<br>".join(links))

    get_products.short_description = _('Товары')
    get_products.allow_tags = True

    def get_user(self, obj):
        return obj.user.username if obj.user else "Анонимный пользователь"
    get_user.short_description = _('Пользователь')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name',)
    verbose_name = _('Отзыв')
    verbose_name_plural = _('Отзывы')

# Объединяем функциональность SalesReportAdmin и ReportAdmin
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/sales_report.html"
    list_display = ('created_at', 'total_sales', 'total_orders', 'total_customers')
    ordering = ('-created_at',)
    verbose_name = _('Отчёт')
    verbose_name_plural = _('Отчёты')
    def changelist_view(self, request, extra_context=None):
        report = generate_sales_report()
        extra_context = extra_context or {}
        extra_context['report'] = report
        return super().changelist_view(request, extra_context=extra_context)
