from django.contrib import admin
from .models import Product, Order, Review

# Регистрация моделей в админке
admin.site.register(Product)  # Регистрация модели Товар (Product)
admin.site.register(Order)    # Регистрация модели Заказ (Order)
admin.site.register(Review)   # Регистрация модели Отзыв (Review)
