import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("EMAIL_HOST configured as:", settings.EMAIL_HOST)
print("EMAIL_HOST_USER configured as:", settings.EMAIL_HOST_USER)

try:
    send_mail(
        'Test Subject',
        'This is a test message from Django.',
        settings.DEFAULT_FROM_EMAIL,
        ['noreply@flexyridegh.com'],
        fail_silently=False,
    )
    print("Django email sent successfully!")
except Exception as e:
    print(f"Django email failed: {e}")
