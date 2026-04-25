import os
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from core_auth.models import User
from integrations.email_service import EmailService

def trigger_welcome():
    print("--- Triggering System Welcome Email ---")
    unique_id = uuid.uuid4().hex[:6]
    email = f"test_user_{unique_id}@example.com" # This is where the email would go
    
    try:
        # Create a test user
        user = User.objects.create_user(
            email=email,
            password='Password123!',
            role='rider'
        )
        print(f"Created user: {email}")
        
        # Trigger welcome email
        EmailService.send_welcome_email(user)
        print(f"PASS: Welcome email logic triggered for {email}.")
        
    except Exception as e:
        print(f"FAIL: Failed to trigger welcome email. Error: {e}")

if __name__ == "__main__":
    trigger_welcome()
