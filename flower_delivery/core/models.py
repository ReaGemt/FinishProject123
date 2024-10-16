from django.db import models
from django.contrib.auth.models import User

# Модель товара
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.name

# Модель изображения для товара
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/')

# Модель корзины
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='CartItem')

    def __str__(self):
        return f"Корзина пользователя: {self.user.username}"

# Модель элемента корзины (добавили связь с Cart)
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)  # Связь с корзиной
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Связь с продуктом
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

# Модель заказа
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='OrderItem')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Заказ {self.id} пользователя {self.user.username}"

# Модель элемента заказа (добавили связь с Order)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)  # Связь с заказом
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Связь с продуктом
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

# Модель отзыва
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    review_text = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.product.name} by {self.id}"
