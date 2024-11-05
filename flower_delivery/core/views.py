# core\views.py
import logging
import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import Product, Cart, CartItem, Order, OrderItem, Review, Report
from .forms import UserRegisterForm, UserUpdateForm, ProductForm
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .forms import StockUpdateForm
from .utils import generate_sales_report
import csv
from reportlab.lib.pagesizes import letter
from datetime import timedelta
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import datetime
from .forms import UserProfileForm
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg
from django.views.decorators.http import require_POST
from django.db.utils import IntegrityError
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product, Review
from .forms import ReviewForm

logger = logging.getLogger(__name__)

# Constants for working hours
WORKING_HOURS_START = 9  # Начало рабочего времени (9 утра)
WORKING_HOURS_END = 20  # Конец рабочего времени (6 вечера)

date_str = '2024-10-27'
naive_datetime = datetime.strptime(date_str, '%Y-%m-%d')
aware_datetime = timezone.make_aware(naive_datetime)

def is_within_working_hours():
    """Проверяет, находится ли текущее время в пределах рабочего времени."""
    now = timezone.localtime()  # Получаем текущее время в локальном часовом поясе
    return settings.WORKING_HOURS_START <= now.hour < settings.WORKING_HOURS_END

def is_manager(user):
    """Проверяет, является ли пользователь менеджером или администратором."""
    return user.groups.filter(name='Менеджеры').exists() or user.is_superuser

# Функция для проверки, является ли пользователь администратором
def is_admin(user):
    return user.is_staff

@user_passes_test(is_admin)
def update_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = StockUpdateForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail', product_id=product.id)  # Перенаправление после обновления
    else:
        form = StockUpdateForm(instance=product)
    return render(request, 'update_stock.html', {'form': form, 'product': product})

def product_list(request):
    category = request.GET.get('category')
    products = Product.objects.filter(category=category) if category else Product.objects.all()
    # Используйте один из предложенных вариантов ниже
    products = products.order_by('name').select_related('created_by')  # Вариант 1
    # или
    # products = products.order_by('name').only('id', 'name', 'price', 'created_by_id')  # Вариант 2
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'catalog.html', {'page_obj': page_obj, 'products': page_obj.object_list, 'is_paginated': True})


def get_or_create_cart(request):
    """Функция для получения или создания корзины, привязанной к пользователю или сессии"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Используем идентификатор сессии
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        cart, created = Cart.objects.get_or_create(session=session_id)
    return cart

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным числом.")
        if product.stock < quantity:  # Предположим, что есть поле stock для количества товара на складе
            raise ValueError("Недостаточно товара на складе.")
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('view_cart')

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        from django.db.models import F
        cart_item.quantity = F('quantity') + quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    # Очистка кэша корзины, если используется кэширование
    from django.core.cache import cache
    cache.delete(f'cart_{request.user.id}' if request.user.is_authenticated else f'session_{request.session.session_key}')

    message = f'Товар "{product.name}" добавлен в корзину. Количество: {cart_item.quantity}.'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'message': message})

    return redirect('view_cart')


def view_cart(request):
    # Проверка на рабочее время
    if not is_within_working_hours():
        messages.warning(request, "Заказы принимаются только в рабочее время (с 9:00 до 18:00).")

    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    return render(request, 'cart.html', {'cart': cart, 'cart_items': cart_items})

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        try:
            data = json.loads(request.body)
            new_quantity = int(data.get('quantity', 1))
            if new_quantity <= 0:
                raise ValueError("Количество должно быть положительным.")
            cart_item.quantity = new_quantity
            cart_item.save()

            cart_total = cart_item.cart.get_total()
            item_total = cart_item.get_total_price()

            return JsonResponse({'success': True, 'cart_total': cart_total, 'item_total': item_total})
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка обновления корзины: {e}")
            return JsonResponse({'success': False, 'error': 'Invalid quantity'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Товар удалён из корзины.')
    return redirect('view_cart')

from django.shortcuts import redirect, render
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

@login_required
def checkout(request):
    if not is_within_working_hours():
        logger.info("Attempt to place an order outside working hours.")
        messages.error(request, 'Заказы принимаются только в рабочее время (с 9:00 до 18:00).')
        return redirect('view_cart')


    cart = get_or_create_cart(request)
    if not cart.items.exists():
        logger.info("Attempt to checkout with an empty cart.")
        messages.error(request, 'Ваша корзина пуста. Пожалуйста, добавьте товары перед оформлением заказа.')
        return redirect('view_cart')

    if request.method == "POST":
        address = request.POST.get('address')
        comments = request.POST.get('comments', '')
        logger.info(f"Received address: {address}, comments: {comments}")

        try:
            # Создание заказа
            order = Order.objects.create(user=request.user, address=address, comments=comments)
            for item in cart.items.all():
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)

            # Очистка корзины после оформления заказа
            cart.items.all().delete()
            messages.success(request, 'Ваш заказ успешно оформлен.')
            return redirect('order_success', order_id=order.id)

        except Exception as e:
            # Логирование ошибки и сообщение для пользователя
            logger.error(f"Ошибка при оформлении заказа: {e}")
            messages.error(request, 'Ошибка при оформлении заказа. Попробуйте позже.')

    return render(request, 'checkout.html', {'cart': cart})

@login_required
def repeat_order(request, order_id):
    """Функция для повторного заказа."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    new_order = Order.objects.create(user=order.user, address=order.address, comments=order.comments)

    for item in order.items.all():
        OrderItem.objects.create(order=new_order, product=item.product, quantity=item.quantity)

    messages.success(request, 'Повторный заказ успешно оформлен.')
    return redirect('order_history')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    try:
        review = Review.objects.get(product=product, user=request.user)
    except Review.DoesNotExist:
        review = None

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Ваш отзыв добавлен.' if review.created_at == review.updated_at else 'Ваш отзыв обновлён.')
            return redirect('product_detail', product_id=product.id)
    else:
        form = ReviewForm(instance=review)

    return render(request, 'add_review.html', {'product': product, 'form': form})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Регистрация прошла успешно. Добро пожаловать!")
            return redirect('profile')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    # Получаем заказы текущего пользователя
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
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

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})

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
        form = UserProfileForm(request.POST, user=request.user, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль был успешно обновлен.')
            return redirect('profile')
    else:
        form = UserProfileForm(user=request.user, instance=request.user)
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
        query = request.POST.get('query')
        if query:
            api_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
            headers = {
                "Authorization": f"Token {settings.DADATA_API_TOKEN}",
                "Content-Type": "application/json",
            }
            data = {"query": query, "count": 5}
            try:
                response = requests.post(api_url, json=data, headers=headers)
                suggestions = response.json().get('suggestions', [])
                return JsonResponse({'suggestions': suggestions})
            except Exception as e:
                logger.error(f"Ошибка при подключении к DaData: {e}")
                return JsonResponse({'suggestions': [], 'error': 'Service unavailable'})

    return JsonResponse({'suggestions': []})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    total_price = sum(item.get_total_price() for item in order.items.all())
    return render(request, 'order_detail.html', {'order': order, 'total_price': total_price})


def repeat_order(request, order_id):
    """Функция для повторного заказа"""
    original_order = get_object_or_404(Order, id=order_id, user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)

    for item in original_order.items.all():
        # Проверяем, есть ли уже этот товар в корзине
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=item.product)
        if not created:
            cart_item.quantity += item.quantity  # Увеличиваем количество, если товар уже есть
        else:
            cart_item.quantity = item.quantity  # Иначе добавляем новое количество
        cart_item.save()

    messages.success(request, 'Товары из заказа были добавлены в вашу корзину.')
    return redirect('view_cart')

def is_manager(user):
    return user.is_superuser or user.groups.filter(name='Менеджеры').exists()


# core/views.py

from django.contrib.auth.decorators import user_passes_test
from .utils import generate_sales_report_by_custom_period
import plotly.express as px
import plotly.io as pio
from django.shortcuts import render
from datetime import datetime

def is_manager(user):
    return user.is_superuser or user.groups.filter(name='Менеджеры').exists()

def sales_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        start_date = None
        end_date = None

    report = generate_sales_report(start_date=start_date, end_date=end_date)

    # Подготовка данных для графика
    dates = [entry['date'].strftime('%Y-%m-%d') for entry in report['daily_sales']]
    sales = [float(entry['total_sales']) for entry in report['daily_sales']]

    fig = px.line(x=dates, y=sales, labels={'x': 'Дата', 'y': 'Сумма продаж'}, title='Продажи по дням')
    graph_html = fig.to_html(full_html=False)

    return render(request, 'admin/sales_report.html', {
        'report': report,
        'graph_html': graph_html,
        'start_date': start_date_str,
        'end_date': end_date_str,
    })

def download_sales_report_csv(request):
    report = generate_sales_report_by_custom_period()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    # Используем UTF-8 с BOM для корректного отображения в Excel
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response)

    writer.writerow(['Показатель', 'Значение'])
    writer.writerow(['Общий объем продаж', report['total_sales']])
    writer.writerow(['Общее количество заказов', report['total_orders']])
    writer.writerow(['Общее количество клиентов', report['total_customers']])

    return response


def generate_pdf(request):
    # Создаем HTTP-ответ с типом содержимого 'application/pdf'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'

    # Создаем объект canvas для генерации PDF
    p = canvas.Canvas(response, pagesize=letter)

    # Добавляем текст на страницу
    p.drawString(100, 750, "Отчет по продажам")
    p.drawString(100, 700, "Общий доход: 5000 руб.")
    p.drawString(100, 650, "Количество заказов: 200")

    # Заканчиваем страницу и сохраняем PDF
    p.showPage()
    p.save()

    return response


def download_sales_report_pdf(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        # Парсим даты из строк
        naive_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        naive_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Преобразуем в осознанные объекты datetime
        start_date = timezone.make_aware(naive_start_date)
        end_date = timezone.make_aware(naive_end_date)
    else:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        report = generate_sales_report_by_custom_period(start_date, end_date)
        period_description = "за последние 30 дней"

    # Создание PDF отчёта
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Заголовок
    p.drawString(100, 750, f"Отчёт по продажам {period_description}")

    # Данные отчёта
    p.drawString(100, 720, f"Общий объём продаж: {report['total_sales']} руб.")
    p.drawString(100, 700, f"Общее количество заказов: {report['total_orders']}")
    p.drawString(100, 680, f"Общее количество клиентов: {report['total_customers']}")

    # Создание графика с Plotly
    data = {
        "Показатель": ["Продажи", "Заказы", "Клиенты"],
        "Значение": [report['total_sales'], report['total_orders'], report['total_customers']]
    }
    fig = px.bar(data, x="Показатель", y="Значение", title="Отчёт по продажам")
    graph_buffer = BytesIO()
    fig.write_image(graph_buffer, format='png')
    graph_buffer.seek(0)

    # Добавление графика в PDF
    p.drawImage(graph_buffer, 100, 400, width=400, height=200)

    # Завершение PDF
    p.showPage()
    p.save()

    # Сохранение PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    return response


@staff_member_required
def reports_list(request):
    reports = Report.objects.order_by('-created_at')
    return render(request, 'reports/reports_list.html', {'reports': reports})

@staff_member_required
def sales_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        # Парсим даты из строк
        naive_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        naive_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Преобразуем в осознанные объекты datetime
        start_date = timezone.make_aware(naive_start_date)
        end_date = timezone.make_aware(naive_end_date)
    else:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

    # Генерируем отчёт по выбранному периоду
    report = generate_sales_report_by_custom_period(start_date, end_date)

    # Данные для графика
    data = {
        "Показатель": ["Продажи", "Заказы", "Клиенты"],
        "Значение": [report['total_sales'], report['total_orders'], report['total_customers']]
    }

    # Генерация графика с Plotly
    fig = px.bar(data, x="Показатель", y="Значение", title="Отчет по продажам")
    graph_html = fig.to_html(full_html=False)

    # Передаём данные в шаблон
    return render(request, 'admin/sales_report.html', {
        'report': report,
        'graph_html': graph_html,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    })

@staff_member_required
def popular_products_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=30)

    order_items = OrderItem.objects.filter(
        order__created_at__range=[start_date, end_date],
        order__status='delivered'
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum(F('quantity') * F('product__price'))
    ).order_by('-total_quantity')

    context = {
        'order_items': order_items,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    }
    return render(request, 'reports/popular_products_report.html', context)

def catalog(request):
    products = Product.objects.annotate(current_rating=Avg('reviews__rating'))
    return render(request, 'catalog.html', {'products': products})

@csrf_exempt
@login_required
def rate_product(request, product_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rating = int(data.get('rating', 0))
            product = get_object_or_404(Product, id=product_id)
            if not (1 <= rating <= 5):
                return JsonResponse({'success': False, 'error': 'Рейтинг должен быть от 1 до 5'})

            # Создаём или обновляем отзыв
            review, created = Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={'rating': rating}
            )

            # Метод save в модели Review обновит current_rating продукта
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request'})

