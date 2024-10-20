from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

# Инициализация Django для каждого файла теста
import django
django.setup()

class UserAuthTests(TestCase):
    def test_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'password1': 'password123',
            'password2': 'password123',
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'password1': 'password123',
            'password2': 'differentpassword',
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two password fields didn’t match.")

    def test_user_login(self):
        User.objects.create_user(username='testuser', password='password123')
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_invalid_credentials(self):
        User.objects.create_user(username='testuser', password='password123')
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password.")
