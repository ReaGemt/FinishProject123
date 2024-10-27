# core/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Product
from dadata import Dadata
from django.conf import settings
import logging
from django.utils.translation import gettext_lazy as _



logger = logging.getLogger(__name__)

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class AddressForm(forms.Form):
    address = forms.CharField(max_length=255, label='Адрес',
                              widget=forms.TextInput(attrs={'placeholder': 'Введите адрес'}))

    def clean_address(self):
        address = self.cleaned_data['address']
        try:
            dadata = Dadata(settings.DADATA_API_KEY, settings.DADATA_SECRET_KEY)
            result = dadata.suggest("address", address)
            if result and len(result) > 0:
                return result[0]['value']
        except Exception as e:
            logger.error(f"Ошибка при подключении к DaData: {e}")
            raise forms.ValidationError(_("Не удалось определить адрес. Пожалуйста, проверьте введённые данные."))
        finally:
            dadata.close()  # Закрываем соединение

class StockUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['stock']

class SalesReportForm(forms.Form):
    start_date = forms.DateField(
        label='Начало периода',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label='Конец периода',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )