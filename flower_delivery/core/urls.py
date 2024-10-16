# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='catalog'),  # Страница каталога
    path('cart/', views.view_cart, name='view_cart'),  # Страница корзины
    path('checkout/', views.checkout, name='checkout'),  # Оформление заказа
    path('order_history/', views.order_history, name='order_history'),  # История заказов
    path('order_success/', views.order_success, name='order_success'),  # Страница успешного заказа
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),  # Страница товара
    path('add_review/<int:product_id>/', views.add_review, name='add_review'),  # Добавление отзыва
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
