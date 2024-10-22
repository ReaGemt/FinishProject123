# core/admin.py
from django.contrib import admin
from .models import Product, Order, Review, OrderItem
from django.utils.translation import gettext_lazy as _

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'rating', 'is_popular', 'created_by')
    list_filter = ('category', 'is_popular', 'rating')
    search_fields = ('name',)
    verbose_name = _('Продукт')
    verbose_name_plural = _('Продукты')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_products', 'get_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)

    def get_products(self, obj):
        return ", ".join([item.product.name for item in obj.orderitem_set.all()])
    get_products.short_description = _('Товары')

    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = _('Пользователь')
    verbose_name = _('Заказ')
    verbose_name_plural = _('Заказы')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name',)
    verbose_name = _('Отзыв')
    verbose_name_plural = _('Отзывы')
