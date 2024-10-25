# core/models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import os
from django.conf import settings

# Telegram Bot Integration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class ProductManager(models.Manager):
    def popular(self):
        return self.filter(is_popular=True)

# Модель товара
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('roses', _('Розы')),
        ('tulips', _('Тюльпаны')),
        ('orchids', _('Орхидеи')),
        ('bouquets', _('Букеты')),
        ('other', _('Другие')),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='roses')
    is_popular = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    objects = ProductManager()

    def __str__(self):
        return self.name

    def get_category_display(self):
        return dict(self.CATEGORY_CHOICES).get(self.category)

    class Meta:
        verbose_name = _('Продукт')
        verbose_name_plural = _('Продукты')

# Модель корзины
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Корзина пользователя: {self.user.username}"
        return f"Корзина сессии: {self.session}"

    def get_total(self):
        return sum(item.get_total_price() for item in self.items.all())

    class Meta:
        verbose_name = _('Корзина')
        verbose_name_plural = _('Корзины')

# Модель элемента корзины
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def get_total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

    class Meta:
        verbose_name = _('Элемент корзины')
        verbose_name_plural = _('Элементы корзины')

# Модель заказа
# core/models.py

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Ожидание')),
        ('confirmed', _('Подтверждено')),
        ('shipped', _('Отправлено')),
        ('delivered', _('Доставлено')),
        ('canceled', _('Отменено')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Заказ {self.id} - {self.status}'

    def get_products_display(self):
        # Получение списка товаров из заказа и форматирование их для отображения в админке
        order_items = self.items.all()
        products = [f"{item.product.name} (x{item.quantity})" for item in order_items]
        return format_html("<br>".join(products))

    get_products_display.short_description = "Товары"

    def get_total_price(self):
        return sum(item.product.price * item.quantity for item in self.items.all())

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')


# Модель элемента заказа
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    def get_total_price(self):
        return self.product.price * self.quantity

    class Meta:
        verbose_name = _('Элемент заказа')
        verbose_name_plural = _('Элементы заказа')

# Модель отзыва
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Отзыв от {self.user} на {self.product}"

    def clean(self):
        if not (1 <= self.rating <= 5):
            raise ValidationError(_('Рейтинг должен быть от 1 до 5'))
    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        unique_together = ('product', 'user')

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_chat_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Профиль {self.user.username}"