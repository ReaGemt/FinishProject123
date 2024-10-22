from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Product, Order, OrderItem

class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(name="Роза", price=100.00)

    def test_order_creation(self):
        self.client.login(username='testuser', password='password123')
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.post(reverse('checkout'), {'address': 'Test Address'})
        self.assertEqual(response.status_code, 302)  # Проверяем, что произошел редирект (успешное оформление заказа)
        order = Order.objects.filter(user=self.user).first()
        self.assertTrue(order)  # Проверяем, что заказ был создан
        self.assertEqual(order.orderitem_set.first().product.name, "Роза")  # Проверяем, что заказ содержит правильный товар

    def test_order_with_empty_cart(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('checkout'), {'address': 'Test Address'})
        self.assertEqual(response.status_code, 200)  # Проверка, что страница не перенаправляется
        self.assertContains(response, "Ваша корзина пуста.")  # Убедитесь, что сообщение об ошибке отображается


class ProductCatalogTests(TestCase):
    def setUp(self):
        Product.objects.create(name="Роза", price=100.00, category='roses', is_popular=True)
        Product.objects.create(name="Тюльпан", price=80.00, category='tulips')

    def test_filter_by_category(self):
        response = self.client.get(reverse('catalog') + '?category=roses')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Роза")
        self.assertNotContains(response, "Тюльпан")

    def test_pagination(self):
        for i in range(10):
            Product.objects.create(name=f"Цветок {i}", price=50.00)
        response = self.client.get(reverse('catalog'))
        self.assertContains(response, "Цветок 0")
        self.assertContains(response, "Цветок 5")
        self.assertNotContains(response, "Цветок 6")  # Полагаем, что на странице 6 товаров

    def test_popular_products_displayed(self):
        response = self.client.get(reverse('catalog'))
        self.assertContains(response, "Популярно")