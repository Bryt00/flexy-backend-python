import os
import django
import ssl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

# Monkeypatch ssl to ignore certificate errors for smtplib
ssl.create_default_context = ssl._create_unverified_context

from django.core.mail import send_mail
from django.conf import settings

try:
    send_mail(
        'Test email',
        'Hello from FlexyRide! If you are reading this, SMTP is working.',
        settings.DEFAULT_FROM_EMAIL,
        ['kabrytlex2468@gmail.com'],
        fail_silently=False,
    )
    print("Mail sent successfully via SMTP!")
except Exception as e:
    print(f"Error sending mail: {e}")
