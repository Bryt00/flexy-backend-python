import os
import django
import sys
from django.contrib.auth import get_user_model

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from integrations.models import APIKey

User = get_user_model()

def generate_food_delivery_key():
    service_email = "food_integration@flexyride.com"
    service_name = "Food Delivery Integration Service"
    
    # 1. Ensure the partner user exists
    user, created = User.objects.get_or_create(
        email=service_email,
        defaults={
            'role': 'partner',
            'is_active': True
        }
    )
    
    if created:
        user.set_unusable_password()
        user.save()
        print(f"Created new Partner account: {service_email}")
    else:
        # Ensure role is partner
        user.role = 'partner'
        user.save()
        print(f"Using existing Partner account: {service_email}")

    # 2. Generate the API Key
    raw_key, api_key = APIKey.generate_key(user=user, name=service_name)
    
    print("\n" + "="*50)
    print("API KEY GENERATED SUCCESSFULLY")
    print("="*50)
    print(f"Service Name: {service_name}")
    print(f"Partner Email: {service_email}")
    print(f"API Key: {raw_key}")
    print("="*50)
    print("IMPORTANT: Copy this key now. It is hashed and cannot be retrieved again.")
    print("="*50)

if __name__ == "__main__":
    generate_food_delivery_key()
