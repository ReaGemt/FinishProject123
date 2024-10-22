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


class ExtendedOrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(name="Роза", price=100.00)
        self.client.login(username='testuser', password='password123')

    def test_order_creation_with_comment(self):
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.post(reverse('checkout'), {
            'address': 'Test Address',
            'comments': 'Пожалуйста, доставьте к 5 часам.'
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(user=self.user).first()
        self.assertTrue(order)
        self.assertEqual(order.comments, 'Пожалуйста, доставьте к 5 часам.')

    def test_empty_cart_prevents_order(self):
        response = self.client.post(reverse('checkout'), {'address': 'Test Address'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ваша корзина пуста")
