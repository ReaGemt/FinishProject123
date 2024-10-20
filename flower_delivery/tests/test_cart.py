from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Product, Cart, CartItem

class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(name="Роза", price=100.00)
        self.client.login(username='testuser', password='password123')

    def test_add_to_cart(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.get(user=self.user)
        self.assertTrue(CartItem.objects.filter(cart=cart, product=self.product).exists())

    def test_update_cart_quantity(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(reverse('update_cart_item', args=[cart_item.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 302)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

    def test_remove_from_cart(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(reverse('remove_cart_item', args=[cart_item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CartItem.objects.filter(cart=cart, product=self.product).exists())

    def test_add_nonexistent_product_to_cart(self):
        response = self.client.post(reverse('add_to_cart', args=[999]))
        self.assertEqual(response.status_code, 404)
