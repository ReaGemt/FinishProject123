# core/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import Product, Cart, CartItem, Order, OrderItem, Review
from .forms import UserRegisterForm, UserUpdateForm, ProductForm
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render


def product_list(request):
    category = request.GET.get('category')
    products = Product.objects.filter(category=category) if category else Product.objects.all()
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'catalog.html', {'page_obj': page_obj, 'products': page_obj.object_list, 'is_paginated': True})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
    cart_item.save()
    messages.success(request, f'{product.name} добавлен в корзину.')
    return redirect('view_cart')

@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart.html', {'cart': cart})

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == "POST":
        quantity = int(request.POST.get('quantity'))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Количество товара обновлено.')
        else:
            cart_item.delete()
            messages.success(request, 'Товар удалён из корзины.')
    return redirect('view_cart')

@login_required
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == "POST":
        cart_item.delete()
        messages.success(request, 'Товар удалён из корзины.')
    return redirect('view_cart')

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if request.method == "POST":
        address = request.POST.get('address')
        order = Order.objects.create(user=request.user, address=address, total_price=cart.get_total())
        for item in cart.cartitem_set.all():
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
        cart.delete()
        messages.success(request, 'Ваш заказ успешно оформлен.')
        return redirect('order_success')
    return render(request, 'checkout.html', {'cart': cart})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        Review.objects.create(product=product, user=request.user, rating=rating, comment=comment)
        messages.success(request, 'Ваш отзыв добавлен.')
        return redirect('product_detail', product_id=product.id)
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

def is_manager(user):
    return user.groups.filter(name='Менеджеры').exists() or user.is_superuser

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

@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('user_list')
    return render(request, 'delete_user.html', {'user': user})

@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = UserUpdateForm(instance=user)
    return render(request, 'edit_user.html', {'form': form, 'user': user})

def order_success(request):
    return render(request, 'order_success.html')

@user_passes_test(is_manager)
def remove_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Проверка: если пользователь не админ и не создал этот продукт, доступ запрещен
    if request.user != product.created_by and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Товар успешно удалён.')
        return redirect('catalog')

    return render(request, 'confirm_delete.html', {'product': product})