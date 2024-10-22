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
        self.assertContains(response, "Пароли не совпадают.")

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
        self.assertContains(response, "Пожалуйста, введите правильное имя пользователя и пароль.")


class ExtendedUserAuthTests(TestCase):
    def test_registration_with_existing_username(self):
        User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'password1': 'password123',
            'password2': 'password123',
            'email': 'new@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пользователь с таким именем уже существует.")

    def test_password_reset(self):
        user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        response = self.client.post(reverse('password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertContains(response, "Проверьте вашу почту для дальнейших инструкций.")

    def test_update_profile(self):
        user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('edit_profile'), {
            'username': 'updateduser',
            'email': 'updated@example.com'
        })
        user.refresh_from_db()
        self.assertEqual(user.username, 'updateduser')
        self.assertEqual(user.email, 'updated@example.com')