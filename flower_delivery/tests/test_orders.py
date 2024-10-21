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
        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(user=self.user).first()
        self.assertTrue(order)
        self.assertEqual(order.orderitem_set.first().product.name, "Роза")

    def test_order_with_empty_cart(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('checkout'), {'address': 'Test Address'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty.")