import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

# Override settings to test native backend with panel.flexyridegh.com
settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
settings.EMAIL_HOST = 'panel.flexyridegh.com'
settings.EMAIL_PORT = 465
settings.EMAIL_USE_SSL = True

try:
    send_mail(
        'Test email panel host',
        'Testing native SSL with panel.flexyridegh.com',
        settings.DEFAULT_FROM_EMAIL,
        ['kabrytlex2468@gmail.com'],
        fail_silently=False,
    )
    print("Mail sent successfully using panel.flexyridegh.com!")
except Exception as e:
    print(f"Error sending mail: {e}")
