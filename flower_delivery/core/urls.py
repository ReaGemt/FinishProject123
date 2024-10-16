from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='catalog'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order_history/', views.order_history, name='order_history'),
    path('order_success/', views.order_success, name='order_success'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('add_review/<int:product_id>/', views.add_review, name='add_review'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),  # Добавление в корзину
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
