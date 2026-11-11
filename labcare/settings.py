import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-labcare-production-core-system-seed"
BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Secret Key
SECRET_KEY = config('DJANGO_SECRET_KEY')

# 2. Debug Mode (cast to boolean automatically)
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

# 3. Allowed Hosts (parsed as a list from comma-separated string)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv())

# 4. Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backend.sqlite3',#django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
# settings.py
MPESA_ENVIRONMENT = "sandbox"  # Change to 'production' for live payments
MPESA_CONSUMER_KEY =config("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET =config("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")  # Business ShortCode (Till or Paybill)
MPESA_PASSKEY =config("MPESA_PASSKEY")
MPESA_INITIATOR_PHONE = os.getenv("MPESA_INITIATOR_PHONE", "254793294189")  # Test phone for sandbox

# Daraja URLs
if MPESA_ENVIRONMENT == "production":
    MPESA_AUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    MPESA_STK_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    MPESA_CALLBACK_BASE_URL = "https://medrouterrands.com"  # Must be a public HTTPS domain
else:
    MPESA_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    MPESA_STK_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    # For local testing, use ngrok or your Render staging link
    MPESA_CALLBACK_BASE_URL = "https://medrouterrands.com"
ALLOWED_HOSTS = [
    '*',
    'medrouterrands.com',
    'www.medrouterrands.com',]  # Allows Render or any test domain to load the site

CSRF_TRUSTED_ORIGINS = [
    'https://medrouterrands.com',
    'https://www.medrouterrands.com',
    'https://*.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
BASE_URL = "http://localhost:8000"
REF_URL = 'https://medrouterrands.com' 
      
INSTALLED_APPS = [    
    "django.contrib.admin",
    "django.contrib.auth",  
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core.apps.CoreConfig",
    'django.contrib.sitemaps'
]

AUTH_USER_MODEL = "core.User"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- Add this here
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "labcare.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "labcare.wsgi.application"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medroute_db',        # Full Database Name from cPanel
        'USER': 'medroute_Ron',      # Full Database User from cPanel
        'PASSWORD': 'ron123kanyonga456',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ]
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "LabCare Diagnostics Core <operations@medroute.system>"
COMPANY_ALERT_EMAIL = "ronkanyonga@gmail.com"
TIME_ZONE = 'Africa/Nairobi'
USE_TZ = True
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Lax'