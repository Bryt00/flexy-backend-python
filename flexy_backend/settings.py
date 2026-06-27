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

DEBUG = env('DEBUG', default=False)

CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*', '192.168.1.76'])

# Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Determine if we should use GIS (GeoDjango)
# We disable it locally if GDAL is not installed to allow development on Windows without binary hell.
USE_GIS = True
if env('DJANGO_ENV', default='production') == 'local':
    # Try to auto-locate GDAL on Linux (Docker) to avoid ImproperlyConfigured
    import platform
    if platform.system() == 'Linux':
        import glob
        gdal_libs = glob.glob('/usr/lib/libgdal.so*') + glob.glob('/usr/lib/x86_64-linux-gnu/libgdal.so*')
        if gdal_libs:
            os.environ['GDAL_LIBRARY_PATH'] = gdal_libs[0]

    try:
        from django.contrib.gis import gdal
        if not hasattr(gdal, 'HAS_GDAL') or not gdal.HAS_GDAL:
            USE_GIS = False
    except Exception:
        USE_GIS = False

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
]

if USE_GIS:
    INSTALLED_APPS.append('django.contrib.gis')

INSTALLED_APPS += [
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
    'staff_portal',
    'django_ckeditor_5',
    'solo',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
    'default': env.db('DATABASE_URL', default='')   
}

# If GIS is enabled, we MUST use the postgis engine for Postgres
if USE_GIS and DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

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
        'core_auth.authentication.CustomJWTAuthentication',
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
        'anon': '500/day',
        'user': '10000/day',
        'burst': '60/minute',
    }
}

# --- Cache Configuration ---
# Uses Redis on production (set REDIS_URL env var), falls back to LocMemCache for dev.
REDIS_URL = env('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'TIMEOUT': 300,  # Default 5 minutes
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'flexyride-api-cache',
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

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "http://localhost:4200",
    "http://127.0.0.1:4200",
])

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

SWAGGER_UI_SETTINGS = {
    'deepLinking': True,
    'persistAuthorization': True,
    'displayOperationId': True,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=1800),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=60),
    'AUTHORIZATION_HEADER_TYPE': ('Bearer',),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='amqp://guest:guest@localhost:5673//')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6380/1')
REDIS_URL = env('REDIS_URL', default='redis://localhost:6380/0')
CELERY_BEAT_SCHEDULE = {
    'activate-scheduled-rides-every-minute': {
        'task': 'rides.tasks.activate_scheduled_rides',
        'schedule': 60.0,
    },
    'cancel-stale-rides-every-15-seconds': {
        'task': 'rides.tasks.cancel_stale_rides',
        'schedule': 15.0,
    },
    'cancel-stale-deliveries-every-15-seconds': {
        'task': 'rides.tasks.cancel_stale_deliveries',
        'schedule': 15.0,
    },
    'cancel-abandoned-rides-hourly': {
        'task': 'rides.tasks.cancel_abandoned_rides',
        'schedule': 3600.0, # Every hour
    },
    'check-document-expirations-daily': {
        'task': 'notification.tasks.check_document_expirations',
        'schedule': 86400.0,  # Every 24 hours
    },
    'send-driver-birthday-pushes-daily': {
        'task': 'notification.tasks.send_driver_birthday_pushes',
        'schedule': 86400.0,  # Every 24 hours
    },
    'remind-upcoming-scheduled-rides-every-minute': {
        'task': 'rides.tasks.remind_upcoming_scheduled_rides',
        'schedule': 60.0,
    },
}

DOCUMENT_RENEWAL_THRESHOLD_DAYS = 7


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "flexy_backend.custom_layer.UUIDRedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
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
    "SCRIPTS": [
        lambda request: "/static/js/admin_spa_nav.js",
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
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Headquarters & Live Operations",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/headquarters/",
                    },
                    {
                        "title": "User Registry",
                        "icon": "group",
                        "link": "/headquarters/core_auth/user/",
                    },
                    {
                        "title": "User Profiles",
                        "icon": "person",
                        "link": "/headquarters/profiles/profile/",
                    },
                ],
            },
            {
                "title": "Ride-Hailing Operations",
                "items": [
                    {
                        "title": "Active & Past Rides",
                        "icon": "commute",
                        "link": "/headquarters/rides/ride/",
                    },
                    {
                        "title": "Ride Receipts",
                        "icon": "receipt",
                        "link": "/headquarters/rides/ridereceipt/",
                    },
                    {
                        "title": "Vehicle Fleet",
                        "icon": "directions_car",
                        "link": "/headquarters/vehicles/vehicle/",
                    },
                    {
                        "title": "Driver Verifications",
                        "icon": "verified_user",
                        "link": "/headquarters/profiles/driververification/",
                    },
                ],
            },
            {
                "title": "Delivery & Courier Operations",
                "items": [
                    {
                        "title": "Delivery Registry",
                        "icon": "local_shipping",
                        "link": "/headquarters/courier/delivery/",
                    },
                    {
                        "title": "Delivery Categories",
                        "icon": "inventory",
                        "link": "/headquarters/core_settings/deliverycategory/",
                    },
                    {
                        "title": "Delivery Weight Tiers",
                        "icon": "scale",
                        "link": "/headquarters/core_settings/deliveryweighttier/",
                    },
                    {
                        "title": "Delivery Vehicle Types",
                        "icon": "local_shipping",
                        "link": "/headquarters/core_settings/deliveryvehicletype/",
                    },
                ],
            },
            {
                "title": "Subscriptions & Advertising",
                "items": [
                    {
                        "title": "Subscription Plans",
                        "icon": "card_membership",
                        "link": "/headquarters/subscriptions/subscriptionplan/",
                    },
                    {
                        "title": "Driver Subscriptions",
                        "icon": "subscriptions",
                        "link": "/headquarters/subscriptions/driversubscription/",
                    },
                    {
                        "title": "Subscription Payments",
                        "icon": "payment",
                        "link": "/headquarters/subscriptions/subscriptionpayment/",
                    },
                    {
                        "title": "Ad Management",
                        "icon": "ads_click",
                        "link": "/headquarters/advertising/adbooking/",
                    },
                    {
                        "title": "Ad Slot Capacity",
                        "icon": "inventory_2",
                        "link": "/headquarters/advertising/adslotcapacity/",
                    },
                    {
                        "title": "Ad Extensions",
                        "icon": "extension",
                        "link": "/headquarters/advertising/adextension/",
                    },
                    {
                        "title": "Ad Analytics",
                        "icon": "analytics",
                        "link": "/headquarters/advertising/adanalytics/",
                    },
                ],
            },
            {
                "title": "Marketing & Communications",
                "items": [
                    {
                        "title": "Promo Codes & Coupons",
                        "icon": "confirmation_number",
                        "link": "/headquarters/marketing/promocode/",
                    },
                    {
                        "title": "App Campaign Banners",
                        "icon": "view_carousel",
                        "link": "/headquarters/marketing/campaign/",
                    },
                    {
                        "title": "Push Campaigns",
                        "icon": "campaign",
                        "link": "/headquarters/notification/campaign/",
                    },
                    {
                        "title": "Sent Notifications Log",
                        "icon": "notifications",
                        "link": "/headquarters/notification/notification/",
                    },
                ],
            },
            {
                "title": "Financial Operations",
                "items": [
                    {
                        "title": "User Wallets",
                        "icon": "account_balance_wallet",
                        "link": "/headquarters/payments/wallet/",
                    },
                    {
                        "title": "Transaction Logs",
                        "icon": "receipt_long",
                        "link": "/headquarters/payments/transaction/",
                    },
                ],
            },
            {
                "title": "Safety, Security & Support",
                "items": [
                    {
                        "title": "Incident Hub (SOS)",
                        "icon": "report_problem",
                        "link": "/headquarters/rides/incident/",
                    },
                    {
                        "title": "Fraud Flags",
                        "icon": "gpp_bad",
                        "link": "/headquarters/audit/fraudflag/",
                    },
                    {
                        "title": "Account Deletion Requests",
                        "icon": "person_remove",
                        "link": "/headquarters/core_auth/deletionrequest/",
                    },
                    {
                        "title": "System Audit Logs",
                        "icon": "history",
                        "link": "/headquarters/audit/auditlog/",
                    },
                    {
                        "title": "API Keys / Integrations",
                        "icon": "api",
                        "link": "/headquarters/integrations/apikey/",
                    },
                    {
                        "title": "File Cloud Metadata",
                        "icon": "cloud",
                        "link": "/headquarters/file_manager/filemetadata/",
                    },
                ],
            },
            {
                "title": "System Parameters & Configurations",
                "items": [
                    {
                        "title": "Pricing & Surge Rules",
                        "icon": "payments",
                        "link": "/headquarters/core_settings/pricingrule/",
                    },
                    {
                        "title": "Vehicle Categories",
                        "icon": "category",
                        "link": "/headquarters/core_settings/vehiclecategory/",
                    },
                    {
                        "title": "Distance Tiers",
                        "icon": "straighten",
                        "link": "/headquarters/core_settings/distancetier/",
                    },
                    {
                        "title": "Global System Settings",
                        "icon": "settings",
                        "link": "/headquarters/core_settings/sitesetting/",
                    },
                ],
            },
            {
                "title": "Public Website Content",
                "items": [
                    {
                        "title": "Blog Posts",
                        "icon": "article",
                        "link": "/headquarters/website/blogpost/",
                    },
                    {
                        "title": "Service Categories",
                        "icon": "directions_car",
                        "link": "/headquarters/website/servicecategory/",
                    },
                    {
                        "title": "Safety Features",
                        "icon": "security",
                        "link": "/headquarters/website/safetyfeature/",
                    },
                    {
                        "title": "FAQ Items",
                        "icon": "quiz",
                        "link": "/headquarters/website/faqitem/",
                    },
                    {
                        "title": "Cities Offered",
                        "icon": "location_city",
                        "link": "/headquarters/website/city/",
                    },
                    {
                        "title": "User Testimonials",
                        "icon": "format_quote",
                        "link": "/headquarters/website/testimonial/",
                    },
                    {
                        "title": "Hero Banners",
                        "icon": "panorama",
                        "link": "/headquarters/website/herobanner/",
                    },
                    {
                        "title": "Job Openings",
                        "icon": "work",
                        "link": "/headquarters/website/jobopening/",
                    },
                    {
                        "title": "Brand Features",
                        "icon": "star",
                        "link": "/headquarters/website/brandfeature/",
                    },
                    {
                        "title": "Website Global Settings",
                        "icon": "tune",
                        "link": "/headquarters/website/websitesettings/",
                    },
                    {
                        "title": "Contact Inquiries",
                        "icon": "mail",
                        "link": "/headquarters/website/contactinquiry/",
                    },
                    {
                        "title": "Legal Documents",
                        "icon": "description",
                        "link": "/headquarters/website/legaldocument/",
                    },
                ],
            },
            {
                "title": "Quick Portals",
                "items": [
                    {
                        "title": "Staff Portal",
                        "icon": "badge",
                        "link": "/portal/",
                    },
                    {
                        "title": "Ad Dashboard",
                        "icon": "campaign",
                        "link": "/advertise/",
                    },
                    {
                        "title": "Public Website",
                        "icon": "public",
                        "link": "/",
                    },
                ],
            },
        ],
    },
    "TABS": [], # Ensures layout consistency
    "CONTAINER": {
        "max_width": "full", # Fixes the "centered content" issue
    },
}

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# Paystack Configuration
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')

# Social Auth Configuration
GOOGLE_OAUTH_CLIENT_ID = env('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = env('GOOGLE_OAUTH_CLIENT_SECRET', default='')
APPLE_OAUTH_CLIENT_ID = env('APPLE_OAUTH_CLIENT_ID', default='')

# Email Configuration (SMTP Details)
SITE_URL = env('SITE_URL', default='https://flexyride.com')
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='flexyridegh.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=465)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='FlexyRide <noreply@flexyridegh.com>')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@flexyridegh.com')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'website': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Ensure the logs directory exists
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

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
        'toolbar': [
            'heading', '|', 
            'bold', 'italic', 'underline', 'link', '|', 
            'bulletedList', 'numberedList', 'outdent', 'indent', '|', 
            'blockQuote', 'insertImage', 'insertTable', '|', 
            'sourceEditing', 'removeFormat'
        ],
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

# --- PUSH NOTIFICATIONS ---
ACTIVE_PUSH_PROVIDER = 'notification.providers.fcm.FCMProvider'
FIREBASE_CREDENTIALS_RELATIVE_PATH = env('FIREBASE_CREDENTIALS_PATH', default='firebase-service-account.json')
if os.path.isabs(FIREBASE_CREDENTIALS_RELATIVE_PATH):
    FIREBASE_CREDENTIALS_PATH = FIREBASE_CREDENTIALS_RELATIVE_PATH
else:
    FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, FIREBASE_CREDENTIALS_RELATIVE_PATH)

