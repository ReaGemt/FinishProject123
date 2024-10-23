# core/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import Product, Cart, CartItem, Order, OrderItem, Review
from .forms import UserRegisterForm, UserUpdateForm, ProductForm
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from dadata import Dadata
from django.conf import settings
import json
import requests

# Utility functions
def is_manager(user):
    """Проверяет, является ли пользователь менеджером или администратором."""
    return user.groups.filter(name='Менеджеры').exists() or user.is_superuser

def is_admin(user):
    """Проверяет, является ли пользователь администратором."""
    return user.is_superuser

def product_list(request):
    category = request.GET.get('category')
    products = Product.objects.filter(category=category) if category else Product.objects.all()
    # Добавьте сортировку по умолчанию (например, по имени или дате создания)
    products = products.order_by('name')  # или 'created_at', если это более подходящий вариант
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'catalog.html', {'page_obj': page_obj, 'products': page_obj.object_list, 'is_paginated': True})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Получаем или создаем элемент корзины
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
    cart_item.save()

    # Добавление отладочных сообщений
    print(
        f"Добавлено в корзину: {cart_item.product.name}, количество: {cart_item.quantity}, пользователь: {request.user}")

    messages.success(request, 'Товар добавлен в корзину.')
    return redirect('view_cart')

@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()  # Правильный доступ к элементам корзины
    print(cart_items)
    return render(request, 'cart.html', {'cart': cart, 'cart_items': cart_items})






@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Количество товара обновлено.')
        else:
            cart_item.delete()
            messages.success(request, 'Товар удалён из корзины.')
        return JsonResponse({
            'success': True,
            'item_total': cart_item.get_total_price(),
            'cart_total': cart_item.cart.get_total()
        })
    return JsonResponse({'success': False})

@login_required
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Товар удалён из корзины.')
    return redirect('view_cart')

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if request.method == "POST":
        address = request.POST.get('address')
        order = Order.objects.create(user=request.user, address=address)
        for item in cart.items.all():
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
        cart.items.all().delete()
        messages.success(request, 'Ваш заказ успешно оформлен.')
        return redirect('order_success')
    return render(request, 'checkout.html', {'cart': cart})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment and 1 <= int(rating) <= 5:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment
            )
            return redirect('product_detail', product_id=product.id)
        else:
            return render(request, 'add_review.html', {
                'product': product,
                'errors': ["Некорректные данные. Пожалуйста, укажите правильный рейтинг (от 1 до 5) и комментарий."]
            })

    return render(request, 'add_review.html', {'product': product})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно. Добро пожаловать!')
            return redirect('profile')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'profile.html', {'orders': orders})

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

@user_passes_test(is_manager)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, 'Товар успешно добавлен.')
            return redirect('catalog')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})

@user_passes_test(is_manager)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user != product.created_by and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар успешно обновлён.')
            return redirect('catalog')
    else:
        form = ProductForm(instance=product)

    return render(request, 'edit_product.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('user_list')
    raise PermissionDenied

@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль пользователя успешно обновлён.')
            return redirect('user_list')
    else:
        form = UserUpdateForm(instance=user)

    return render(request, 'edit_user.html', {'form': form, 'user': user})

def order_success(request):
    return render(request, 'order_success.html')

@user_passes_test(is_manager)
def remove_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user != product.created_by and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Товар успешно удалён.')
        return redirect('catalog')

    return render(request, 'confirm_delete.html', {'product': product})

@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})

def send_message(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")
        recaptcha_response = request.POST.get("g-recaptcha-response")

        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        response = requests.post(verify_url, data=data)
        result = response.json()

        if result.get('success'):
            send_mail(
                subject=f"Новое сообщение от {name}",
                message=f"От {name} ({email}):\n\n{message}",
                from_email=email,
                recipient_list=["info@flowerdelivery.ru"],
            )
            messages.success(request, "Ваше сообщение успешно отправлено!")
            return redirect("contact")
        else:
            messages.error(request, "Не удалось пройти проверку reCAPTCHA. Попробуйте еще раз.")
            return redirect("contact")

    return render(request, "contact.html")

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль был успешно обновлен.')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'edit_user.html', {'form': form, 'user': request.user})

def change_currency(request):
    currency = request.GET.get('currency', 'rub')
    request.session['currency'] = currency
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

@login_required
def request_user_data(request):
    user_data = {
        'username': request.user.username,
        'email': request.user.email,
    }
    return JsonResponse(user_data)

@login_required
def delete_user_account(request):
    request.user.delete()
    return redirect('home')

def suggest_address(request):
    if request.method == 'POST':
        dadata = Dadata(settings.DADATA_API_KEY, settings.DADATA_SECRET_KEY)
        query = request.POST.get('query')
        suggestions = dadata.suggest("address", query)
        return JsonResponse({'suggestions': suggestions})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})
