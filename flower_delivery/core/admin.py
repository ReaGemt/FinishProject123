# core/admin.py
from django.contrib import admin
from .models import Product, Order, Review, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'is_popular', 'created_by')
    list_filter = ('category', 'is_popular')
    search_fields = ('name',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_products', 'get_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)

    def get_products(self, obj):
        # Отображение всех товаров, связанных с заказом
        return ", ".join([item.product.name for item in obj.orderitem_set.all()])
    get_products.short_description = 'Товары'

    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'Пользователь'

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name',)
