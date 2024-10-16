from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product, Cart, CartItem, Order, OrderItem, Review
from django.contrib import messages
from django.contrib.auth import login
from .forms import UserRegisterForm



def product_list(request):
    products = Product.objects.all()
    return render(request, 'catalog.html', {'products': products})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('view_cart')

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart.html', {'cart': cart})

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    if request.method == "POST":
        address = request.POST.get('address')
        order = Order.objects.create(user=request.user, address=address, total_price=cart.get_total())
        for item in cart.cartitem_set.all():
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
        cart.delete()
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
        return redirect('product_detail', product_id=product.id)
    return render(request, 'add_review.html', {'product': product})

def order_success(request):
    return render(request, 'order_success.html')

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Авторизация после регистрации
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('profile')  # Перенаправление в личный кабинет
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    # Получаем заказы текущего пользователя
    orders = Order.objects.filter(user=request.user)
    return render(request, 'profile.html', {'orders': orders})

# Добавляем представление для страницы "О нас"
def about(request):
    return render(request, 'about.html')

# Добавляем представление для страницы "Контакты"
def contact(request):
    return render(request, 'contact.html')