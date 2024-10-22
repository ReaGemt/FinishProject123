# core/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Основные маршруты каталога и товаров
    path('', views.product_list, name='catalog'),  # Главная страница каталога
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),  # Детали продукта
    path('add_review/<int:product_id>/', views.add_review, name='add_review'),  # Добавление отзыва

    # Маршруты для работы с корзиной
    path('cart/', views.view_cart, name='view_cart'),  # Просмотр корзины
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),  # Добавление в корзину
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),  # Обновление корзины
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),  # Удаление из корзины

    # Маршруты для оформления заказа
    path('checkout/', views.checkout, name='checkout'),  # Оформление заказа
    path('order_history/', views.order_history, name='order_history'),  # История заказов
    path('order_success/', views.order_success, name='order_success'),  # Успешный заказ

    # Маршруты для работы с пользователями и профилем
    path('profile/', views.profile, name='profile'),  # Профиль пользователя
    path('register/', views.register, name='register'),  # Регистрация
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),  # Выход из аккаунта

    # Управление пользователями (администратором)
    path('users/', views.user_list, name='user_list'),  # Список пользователей
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),  # Редактирование пользователя
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),  # Удаление пользователя

    # Управление продуктами (администратором/менеджером)
    path('products/add/', views.add_product, name='add_product'),  # Добавление продукта
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),  # Редактирование продукта
    path('products/remove/<int:product_id>/', views.remove_product, name='remove_product'),  # Удаление продукта

    # Статические страницы
    path('about/', views.about, name='about'),  # О компании
    path('contact/', views.contact, name='contact'),  # Контакты

    # Дополнительно: Восстановление пароля (опционально)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Дополнительно: Отправка сообщения
    path("send_message/", views.send_message, name="send_message"),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change_currency/', views.change_currency, name='change_currency'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('dadata/suggest-address/', views.suggest_address, name='suggest_address'),
]
