# core/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Product, Order, Review, OrderItem
from django.utils.translation import gettext_lazy as _

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'rating', 'is_popular', 'created_by')
    list_filter = ('category', 'is_popular', 'rating')
    search_fields = ('name',)
    verbose_name = _('Продукт')
    verbose_name_plural = _('Продукты')

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Order

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
        return mark_safe("<br>".join(links))  # Используем <br> для лучшего отображения

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
