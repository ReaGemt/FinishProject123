# core/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Product, Cart, CartItem, Order, OrderItem
from django.db.models.signals import post_save
from django.test import TestCase
from .models import Order
from unittest.mock import patch

class ProductModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(
            name='Розы',
            description='Красные розы',
            price=50.00,
            category='roses',
            created_by=self.user
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Розы')
        self.assertEqual(self.product.price, 50.00)
        self.assertEqual(self.product.category, 'roses')
        self.assertEqual(self.product.created_by, self.user)

class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(
            name='Розы',
            description='Красные розы',
            price=50.00,
            category='roses',
            created_by=self.user
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_add_item_to_cart(self):
        cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.assertEqual(cart_item.get_total_price(), 100.00)
        self.assertEqual(self.cart.get_total(), 100.00)

    def test_cart_total(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        total = self.cart.get_total()
        self.assertEqual(total, 100.00)

class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(
            name='Розы',
            description='Красные розы',
            price=50.00,
            category='roses',
            created_by=self.user
        )
        self.order = Order.objects.create(user=self.user, status='pending')

    def test_create_order(self):
        order_item = OrderItem.objects.create(order=self.order, product=self.product, quantity=3)
        self.assertEqual(order_item.quantity, 3)
        self.assertEqual(order_item.get_total_price(), 150.00)

    def test_order_total(self):
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1)
        total_price = sum(item.get_total_price() for item in self.order.items.all())
        self.assertEqual(total_price, 150.00)

class UserAuthTests(TestCase):
    def test_user_registration(self):
        user = User.objects.create_user(username='testuser', password='password')
        self.assertIsNotNone(user)

    def test_user_login(self):
        user = User.objects.create_user(username='testuser', password='password')
        login = self.client.login(username='testuser', password='password')
        self.assertTrue(login)
        invalid_login = self.client.login(username='invaliduser', password='wrongpassword')
        self.assertFalse(invalid_login)


    def test_create_order_authenticated(self):
        user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        # Создание продукта для добавления в корзину
        product = Product.objects.create(
            name='Розы',
            description='Красные розы',
            price=50.00,
            category='roses',
            created_by=user
        )
        response = self.client.post(f'/add_to_cart/{product.id}/', {'quantity': 1})
        self.assertEqual(response.status_code, 302)  # Ожидание успешного редиректа

class OrderSignalTests(TestCase):
    @patch('core.signals.send_telegram_message')
    def test_notify_admin_order_created_signal(self, mock_send_message):
        user = User.objects.create_user(username='testuser', password='password')
        order = Order.objects.create(user=user, status='pending')
        from flower_delivery.flower_delivery import settings
        mock_send_message.assert_called_once_with(settings.ADMIN_TELEGRAM_CHAT_ID, f"Новый заказ создан: #{order.id} пользователем {user.username}.")