from django.test import TestCase
from django.urls import reverse
from .models import Product, Cart, CartItem
from django.contrib.auth.models import User

class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(name='Роза', price=100)
        self.client.login(username='testuser', password='password')

    def test_add_to_cart(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.cartitem_set.count(), 1)
        self.assertEqual(cart.cartitem_set.first().product, self.product)
