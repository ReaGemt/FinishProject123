# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from telegram import Bot
from django.utils.translation import gettext_lazy as _
import os

# Модель товара
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('roses', _('Розы')),
        ('tulips', _('Тюльпаны')),
        ('orchids', _('Орхидеи')),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='roses')
    is_popular = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Продукт')
        verbose_name_plural = _('Продукты')

# Модель корзины
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='CartItem')

    def __str__(self):
        return f"Корзина пользователя: {self.user.username}"

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
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Ожидание')),
        ('confirmed', _('Подтверждено')),
        ('shipped', _('Отправлено')),
        ('delivered', _('Доставлено')),
        ('canceled', _('Отменено')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Заказ {self.id} - {self.status}'

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')

# Модель элемента заказа
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

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

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')

# Telegram Bot Integration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@receiver(post_save, sender=Order)
def send_order_status_update(sender, instance, **kwargs):
    if TELEGRAM_BOT_TOKEN:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        user = instance.user
        status = instance.get_status_display()

        # Проверьте наличие telegram_chat_id у пользователя
        if hasattr(user, 'profile') and user.profile.telegram_chat_id:
            chat_id = user.profile.telegram_chat_id
            message = f"Ваш заказ #{instance.id} обновлен. Новый статус: {status}."
            bot.send_message(chat_id=chat_id, text=message)
        else:
            print("Telegram chat ID не найден у пользователя.")
    else:
        print("Telegram Bot Token отсутствует.")
