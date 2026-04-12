"""
Django settings for flexy_backend project.
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
    'core_settings',
    'drf_spectacular',
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FlexyRide API',
    'DESCRIPTION': 'Consolidated Backend API for FlexyRide Fleet Management and Mobile Apps.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTHORIZATION_HEADER_TYPE': ('Bearer',),
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env('REDIS_URL', default="redis://localhost:6379/2")],
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
        "show_search": True,
        "show_all_applications": True,
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
