"""
Django settings for flexy_backend project.
(Forced reload to sync OpenAPI/Serializer changes)
"""

import os
from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True)
)

# Read from .env if exists
environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure--2igbe1w0zqjl_(8w2)irn!e-8_+a(rse0z9fe)uzbf1#20^ah')

DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'daphne',
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    
    # Needs GDAL/GEOS installed on OS level
    # 'django.contrib.gis',
    
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',

    'core_auth',
    'profiles',
    'vehicles',
    'rides',
    'payments',
    'audit',
    'courier',
    'file_manager',
    'marketing',
    'notification',
    'subscriptions',
    'core_settings',
    'drf_spectacular',
    'corsheaders',
    'integrations',
    'website',
    'advertising',
    'django_ckeditor_5',
    'solo',
]

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

# Initialize Sentry
SENTRY_DSN = env('SENTRY_DSN', default=None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Priority for CORS
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'flexy_backend.urls'
APPEND_SLASH = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'website' / 'templates',
            BASE_DIR / 'advertising' / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'flexy_backend.wsgi.application'
ASGI_APPLICATION = 'flexy_backend.asgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:ravendb@localhost:5432/flexyride_db')
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

AUTH_USER_MODEL = 'core_auth.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'integrations.authentication.APIKeyAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'burst': '10/minute',
    }
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FlexyRide API',
    'DESCRIPTION': 'Consolidated Backend API for FlexyRide Fleet Management and Mobile Apps.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_SPLIT_REQUEST': True,
    'SECURITY': [{
        'ApiKeyAuth': [],
        'jwtAuth': []
    }],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-Api-Key',
                'description': 'Enter your API key in the format: fx_prefix_secret'
            },
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    }
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://192.168.0.101:4200",
    "http://192.168.0.101",
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

SWAGGER_UI_SETTINGS = {
    'deepLinking': True,
    'persistAuthorization': True,
    'displayOperationId': True,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTHORIZATION_HEADER_TYPE': ('Bearer',),
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='amqp://guest:guest@localhost:5672//')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BEAT_SCHEDULE = {
    'activate-scheduled-rides-every-minute': {
        'task': 'rides.tasks.activate_scheduled_rides',
        'schedule': 60.0,
    },
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "flexy_backend.custom_layer.UUIDRedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

UNFOLD = {
    "SITE_TITLE": "FlexyRide Admin",
    "SITE_HEADER": "FlexyRide Management",
    "SITE_SYMBOL": "speed", # Material icon
    "SITE_LOGO": "/static/vectors/logo.svg", # Use absolute path
    "DASHBOARD": "flexy_backend.dashboard.dashboard_callback",
    "STYLES": [
        lambda request: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap",
        lambda request: "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200",
        lambda request: "/static/css/admin_theme.css",
    ],
    "COLORS": {
        "primary": {
            "50": "240 100% 98%",
            "100": "240 100% 94%",
            "200": "240 100% 86%",
            "300": "240 100% 74%",
            "400": "240 100% 60%",
            "500": "198 100% 50%", # #00B4FF
            "600": "198 100% 40%",
            "700": "198 100% 30%",
            "800": "198 100% 20%",
            "900": "198 100% 10%",
        },
        "accent": {
            "50": "84 100% 98%",
            "100": "84 100% 94%",
            "200": "84 100% 86%",
            "300": "84 100% 74%",
            "400": "84 100% 60%",
            "500": "81 81% 55%", # #A3E635
            "600": "81 81% 45%",
            "700": "81 81% 35%",
            "800": "81 81% 25%",
            "900": "81 81% 15%",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Operations",
                "items": [
                    {
                        "title": "Dashboard / Live Map",
                        "icon": "map",
                        "link": "/admin/",
                    },
                    {
                        "title": "Rides",
                        "icon": "commute",
                        "link": "/admin/rides/ride/",
                    },
                    {
                        "title": "Vehicle Fleet",
                        "icon": "directions_car",
                        "link": "/admin/vehicles/vehicle/",
                    },
                ],
            },
            {
                "title": "Security & Support",
                "items": [
                    {
                        "title": "Incident Hub (SOS)",
                        "icon": "report_problem",
                        "link": "/admin/rides/incident/",
                    },
                    {
                        "title": "Fraud Flags",
                        "icon": "gpp_bad",
                        "link": "/admin/audit/fraudflag/",
                    },
                    {
                        "title": "API Keys / Integrations",
                        "icon": "vcl",
                        "link": "/admin/integrations/apikey/",
                    },
                ],
            },
            {
                "title": "System Settings",
                "items": [
                    {
                        "title": "Pricing & Surge",
                        "icon": "payments",
                        "link": "/admin/core_settings/pricingrule/",
                    },
                    {
                        "title": "Global Settings",
                        "icon": "settings",
                        "link": "/admin/core_settings/sitesetting/",
                    },
                ],
            },
        ],
    },
}

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# Paystack Configuration
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')

# Email Configuration (SMTP Details)
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='flexyridegh.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=465)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='FlexyRide <noreply@flexyridegh.com>')

# Settings for django-ckeditor-5
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', 'imageUpload', ],
    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
        'code','subscript', 'superscript', 'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|',  'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable',],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side',  '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]
        },
        'heading': {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    }
}

# Paystack Configuration
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')
