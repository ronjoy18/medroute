import os
from pathlib import Path
from decouple import config, Csv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
# labcare/middleware.py
from django.http import HttpResponseForbidden


SESSION_COOKIE_AGE = 2592000  # 30 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
BLOCKED_USER_AGENTS = ['sqlmap', 'nikto', 'nmap', 'masscan']

class ThreatMitigationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        # Drop scanning tools immediately
        if any(scanner in user_agent for scanner in BLOCKED_USER_AGENTS):
            return HttpResponseForbidden("Forbidden: Malicious activity detected.")

        return self.get_response(request)
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        # Adjust traces_sample_rate to capture performance metrics (10% sample)
        traces_sample_rate=0.1,
        # Mask sensitive patient parameters
        send_default_pii=False,
    )
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('DJANGO_SECRET_KEY')
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv())
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
# Prevent cookies from being intercepted over plain HTTP
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Mitigate XSS attacks by blocking JavaScript access to session tokens
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Enforce strict cross-site request handling
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# HTTP Strict Transport Security (HSTS) - Tells browsers to only connect via HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevent content sniffing and clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
# Lock out after 5 consecutive failed attempts
AXES_FAILURE_LIMIT = 5
# Lockout duration in hours (cool-off period)
AXES_COOLOFF_TIME = 2  # 2 hours
# Track both username and client IP address combined
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
# Reset counter automatically on successful login
AXES_RESET_ON_SUCCESS = True
#DATABASES = {
 #   'default': {
  #      'ENGINE': 'django.db.backends.mysql',
   #     'NAME': config('DB_NAME'),
    #    'USER': config('DB_USER'),
     #   'PASSWORD': config('DB_PASSWORD'),
      #  'HOST': config('DB_HOST', default='localhost'),
       # 'PORT': config('DB_PORT', default='3306'),
        #'OPTIONS': {
         #   'charset': 'utf8mb4',
          #  'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#        },
 #   }
#}
# settings.py
MPESA_ENVIRONMENT = "sandbox"  # Change to 'production' for live payments
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "Sp7I0mZeGRoA6VRwbtrA5jnJO4djJtWATUmzsn7fptwjpRUX")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "Qatn7OGki4GEI9vUIkSRiMc4mxkxxW0hW09F78J93SHUNYIAC5BALiaxji7M0NET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")  # Business ShortCode (Till or Paybill)
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
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
    'django.contrib.sitemaps',
    'axes'
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
    "axes.middleware.AxesMiddleware",
    
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
        'ENGINE': 'django.db.backends.sqlite3',  # Use 'django.db.backends.mysql' for MySQL
        'NAME': BASE_DIR / "db.sqlite3",
    }
}

       # 'OPTIONS': {
          #  'charset': 'utf8mb4',
          #  'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
       # },
   # }
#}

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