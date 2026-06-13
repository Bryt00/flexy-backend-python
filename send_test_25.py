import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

# Override settings
settings.EMAIL_PORT = 25
settings.EMAIL_USE_TLS = False
settings.EMAIL_USE_SSL = False

try:
    send_mail(
        'Test email Port 25',
        'Testing port 25 without encryption.',
        settings.DEFAULT_FROM_EMAIL,
        ['kabrytlex2468@gmail.com'],
        fail_silently=False,
    )
    print("Mail sent successfully via Port 25!")
except Exception as e:
    print(f"Error sending mail: {e}")
