import os
import django
from django.core import mail

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

def test_smtp():
    print("--- Testing SMTP Connection ---")
    try:
        with mail.get_connection() as connection:
            mail.EmailMessage(
                subject='FlexyRide SMTP Test',
                body='This is a test email from FlexyRide backend.',
                from_email='noreply@flexyridegh.com',
                to=['noreply@flexyridegh.com'], # Sending to self for test
                connection=connection,
            ).send()
        print("PASS: SMTP email sent successfully.")
    except Exception as e:
        print(f"FAIL: SMTP email failed. Error: {e}")

if __name__ == "__main__":
    test_smtp()
