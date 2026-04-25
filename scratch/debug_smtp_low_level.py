import smtplib
import ssl
from django.conf import settings
import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

def debug_smtp():
    print(f"DEBUG: Host={settings.EMAIL_HOST}, Port={settings.EMAIL_PORT}, User={settings.EMAIL_HOST_USER}")
    
    try:
        # Create an SSL context that ignores certificate errors
        context = ssl._create_unverified_context()
        
        # Port 587 uses STARTTLS
        print("Connecting to server...")
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10)
        print("Connection established. Sending EHLO...")
        server.ehlo()
        
        if settings.EMAIL_USE_TLS:
            print("Starting TLS (ignoring cert errors)...")
            server.starttls(context=context)
            print("TLS started. Sending EHLO again...")
            server.ehlo()
            
        print("Logging in...")
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        print("Login SUCCESS!")
        
        print("Sending test mail...")
        msg = f"Subject: SMTP Debug Test\n\nThis is a debug test from smtplib."
        server.sendmail(settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER], msg)
        print("Mail SENT!")
        
        server.quit()
        print("Closed connection.")
        
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    debug_smtp()
