# core/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Product
from dadata import Dadata
from django.conf import settings

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
            # Автодополнение и проверка адреса
            result = dadata.suggest("address", address)
            if result:
                return result[0]['value']  # Вернуть подтверждённый адрес
        except Exception as e:
            print(f"Ошибка при подключении к DaData: {e}")
        # Возвращаем исходный адрес, если проверка не прошла
        raise forms.ValidationError("Не удалось определить адрес. Пожалуйста, проверьте введённые данные.")
