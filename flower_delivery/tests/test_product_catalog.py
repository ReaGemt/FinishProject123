from django.test import TestCase
from django.urls import reverse
from .models import Product


class ProductCatalogTests(TestCase):
    def setUp(self):
        # Создание тестовых продуктов
        Product.objects.create(name="Роза", price=100.00, category='roses')
        Product.objects.create(name="Тюльпан", price=80.00, category='tulips')

    def test_product_list_view(self):
        # Проверка, что страница каталога доступна и отображает все продукты
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Роза")
        self.assertContains(response, "Тюльпан")

    def test_product_filter_by_category(self):
        # Проверка, что фильтр по категории работает корректно
        response = self.client.get(reverse('catalog') + '?category=roses')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Роза")
        self.assertNotContains(response, "Тюльпан")

    def test_product_pagination(self):
        # Создание дополнительных продуктов для теста пагинации
        for i in range(10):
            Product.objects.create(name=f"Цветок {i}", price=50.00)

        # Проверка, что страница каталога корректно отображает первую страницу с пагинацией
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Цветок 0")
        self.assertContains(response, "Цветок 5")
        # Убедитесь, что создано всего 12 продуктов и пагинация разделила их на несколько страниц
        self.assertNotContains(response, "Цветок 6")
