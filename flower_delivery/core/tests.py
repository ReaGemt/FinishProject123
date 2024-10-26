from django.test import TestCase
from django.contrib.auth.models import User
from .models import Product, Order, OrderItem

class OrderTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser", password="testpassword")
        self.product = Product.objects.create(name="Тестовый продукт", price=10)

    def test_create_order(self):
        order = Order.objects.create(user=self.user, address="Тестовый адрес")
        OrderItem.objects.create(order=order, product=self.product, quantity=2)

        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.get_total_price(), 20)

    def test_repeat_order(self):
        order = Order.objects.create(user=self.user, address="Тестовый адрес")
        OrderItem.objects.create(order=order, product=self.product, quantity=1)

        response = self.client.get(f'/repeat_order/{order.id}/')
        self.assertEqual(response.status_code, 302)

        new_order = Order.objects.last()
        self.assertEqual(new_order.items.count(), 1)
        self.assertEqual(new_order.get_total_price(), 10)