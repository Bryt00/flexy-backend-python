import os
import sys
import django
from django.core.mail import send_mail
from django.conf import settings

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

def test_smtp():
    print("--- SMTP Connectivity Test ---")
    print(f"Host: {settings.EMAIL_HOST}")
    print(f"Port: {settings.EMAIL_PORT}")
    print(f"Use SSL: {settings.EMAIL_USE_SSL}")
    print(f"Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"User: {settings.EMAIL_HOST_USER}")
    
    try:
        subject = 'FlexyRide SMTP Test'
        message = 'This is a test email from the FlexyRide Backend to verify SMTP configuration after Cloudflare update.'
        recipient_list = [settings.EMAIL_HOST_USER] # Sending to self for verification
        
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        
        if sent:
            print("\nSUCCESS: Email sent successfully!")
        else:
            print("\nFAILURE: Email was not sent.")
            
    except Exception as e:
        print(f"\nERROR: SMTP test failed: {str(e)}")

if __name__ == "__main__":
    test_smtp()
