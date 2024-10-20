from django.test import TestCase
from django.urls import reverse
from .models import Product

class ProductCatalogTests(TestCase):
    def setUp(self):
        Product.objects.create(name="Роза", price=100.00, category='roses')
        Product.objects.create(name="Тюльпан", price=80.00, category='tulips')

    def test_product_list_view(self):
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Роза")
        self.assertContains(response, "Тюльпан")

    def test_product_filter_by_category(self):
        response = self.client.get(reverse('catalog') + '?category=roses')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Роза")
        self.assertNotContains(response, "Тюльпан")

    def test_product_pagination(self):
        for i in range(10):
            Product.objects.create(name=f"Цветок {i}", price=50.00)
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Цветок 0")
        self.assertContains(response, "Цветок 5")
