import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

def verify_api_key_system():
    client = APIClient()
    
    # 1. Create a Partner User
    email = "partner_test@flexyride.com"
    User.objects.filter(email=email).delete()
    user = User.objects.create_user(
        email=email,
        password="PartnerPassword123!",
        role='partner'
    )
    print(f"Created Partner user: {email}")

    # 2. Authenticate as Partner to create an API Key
    client.force_authenticate(user=user)
    
    create_response = client.post('/v1/integrations/keys/', {
        'name': 'Test Integration Service'
    })
    
    if create_response.status_code != 201:
        print(f"FAILED to create API Key: {create_response.data}")
        return

    raw_key = create_response.data['raw_key']
    prefix = create_response.data['prefix']
    print(f"SUCCESS: Created API Key with prefix: {prefix}")
    print(f"Raw Key: {raw_key}")

    # 3. Use the API Key to access a protected resource
    key_client = APIClient()
    # Adding the header
    key_client.credentials(HTTP_X_API_KEY=raw_key)
    
    # Try to get ride estimates (requires authentication)
    # We'll use the coordinates from previous tests
    estimate_response = key_client.get('/v1/rides/estimate/', {
        'pickup_lat': 5.6037,
        'pickup_lng': -0.1870,
        'dropoff_lat': 5.6145,
        'dropoff_lng': -0.1730
    })
    
    print(f"Estimate Request with API Key - Status: {estimate_response.status_code}")
    
    if estimate_response.status_code == 200:
        print("PASS: Successfully authenticated using the generated API Key!")
    else:
        print(f"FAIL: API Key authentication failed. Data: {estimate_response.data}")

if __name__ == "__main__":
    verify_api_key_system()
