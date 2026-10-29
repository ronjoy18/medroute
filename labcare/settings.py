import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-labcare-production-core-system-seed"
DEBUG = True #os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# settings.py
MPESA_ENVIRONMENT = "sandbox"  # Change to 'production' for live payments
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "your_consumer_key")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "your_consumer_secret")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")  # Business ShortCode (Till or Paybill)
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
MPESA_INITIATOR_PHONE = os.getenv("MPESA_INITIATOR_PHONE", "254708374149")  # Test phone for sandbox

# Daraja URLs
if MPESA_ENVIRONMENT == "production":
    MPESA_AUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    MPESA_STK_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    MPESA_CALLBACK_BASE_URL = "https://medroute-xp7i.onrender.com"  # Must be a public HTTPS domain
else:
    MPESA_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    MPESA_STK_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    # For local testing, use ngrok or your Render staging link
    MPESA_CALLBACK_BASE_URL = "https://medroute-xp7i.onrender.com"
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
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
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