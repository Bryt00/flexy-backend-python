import sys
import os
import django
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory

from rides.views import RideViewSet
from core_auth.models import User

def verify_estimates():
    factory = APIRequestFactory()
    view = RideViewSet.as_view({'get': 'estimate'})
    
    # We'll use coordinates that likely have no drivers in our mock setup
    # Or just check the structure
    request = factory.get('/v1/rides/estimate/', {
        'pickup_lat': 5.6037,
        'pickup_lng': -0.1870,
        'dropoff_lat': 5.6145,
        'dropoff_lng': -0.1730
    })
    
    # Authenticate as a user
    user = User.objects.first()
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=user)
    
    response = view(request)
    print(f"Status: {response.status_code}")
    print("Response Data:")
    print(json.dumps(response.data, indent=2))
    
    # Check if 'estimates' contains multiple items and has is_available field
    estimates = response.data.get('estimates', {})
    if len(estimates) > 0:
        first_key = list(estimates.keys())[0]
        if 'is_available' in estimates[first_key] and 'eta_minutes' in estimates[first_key]:
            print("\nPASS: New estimation structure validated.")
        else:
            print("\nFAIL: Missing is_available or eta_minutes fields.")
    else:
        print("\nFAIL: No estimates returned.")

if __name__ == "__main__":
    verify_estimates()
