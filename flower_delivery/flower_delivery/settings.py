from pathlib import Path
from django.utils.translation import gettext_lazy as _
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-aj49+pk6yxa75+a2+nnmh3dwt61ycss^-655+v3z39&3dvmxu1')

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'widget_tweaks',
    'dadata',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'flower_delivery.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'flower_delivery.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'

# Инициализация переменных окружения
env = environ.Env()
environ.Env.read_env('.env')

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="your_bot_token_here")
ADMIN_TELEGRAM_CHAT_ID = env("ADMIN_TELEGRAM_CHAT_ID", default="your_admin_chat_id_here")
ENABLE_TELEGRAM_NOTIFICATIONS = env.bool("ENABLE_TELEGRAM_NOTIFICATIONS", default=True)

# SMTP настройки
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 465
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
ADMIN_EMAIL = env('ADMIN_EMAIL')
ENABLE_EMAIL_NOTIFICATIONS = env.bool("ENABLE_EMAIL_NOTIFICATIONS", default=True)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

COOKIE_CONSENT_NAME = 'cookiesAccepted'
COOKIE_CONSENT_AGE_DAYS = 365

DADATA_API_KEY = env('DADATA_API_KEY')
DADATA_SECRET_KEY = env('DADATA_SECRET_KEY')

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # Две недели
