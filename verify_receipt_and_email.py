import os
import django
import uuid
from django.utils import timezone
from django.core import mail

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

# Force Console Backend for verification
from django.conf import settings
settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

from core_auth.models import User
from rides.models import Ride, RideReceipt
from rest_framework.test import APIClient

def verify_full_flow():
    print("--- Verifying Email Auth & Receipt Flow ---")
    client = APIClient()

    # 1. Test Registration (Welcome Email)
    print("\n[STEP 1: Registration]")
    email = f"rider_{uuid.uuid4().hex[:6]}@flexyride.com"
    reg_data = {
        'email': email,
        'password': 'Password123!',
        'full_name': 'Receipt Tester'
    }
    client.post('/v1/auth/register/', reg_data)
    print("Check console for welcome email.")

    # 2. Test OTP (OTP Email)
    print("\n[STEP 2: OTP Request]")
    client.post('/v1/auth/otp/request/', {'email': email})
    print("Check console for OTP email.")

    # 3. Test Ride Completion (Receipt Generation)
    print("\n[STEP 3: Ride Completion]")
    user = User.objects.get(email=email)
    ride = Ride.objects.create(
        rider=user,
        pickup_lat=6.0, pickup_lng=-0.2,
        dropoff_lat=6.1, dropoff_lng=-0.1,
        status='accepted',
        # Set ledger fields and final calculations
        base_fare_ledger=18.0,
        distance_fare_ledger=25.0,
        waiting_fare_ledger=2.0,
        total_calculated_fare=45.0
    )
    
    # Trigger status change to completed
    client.force_authenticate(user=user)
    response = client.patch(f'/v1/rides/{ride.id}/status/', {'status': 'completed'})
    
    # Check if receipt exists
    receipt_exists = RideReceipt.objects.filter(ride=ride).exists()
    if receipt_exists:
        receipt = RideReceipt.objects.get(ride=ride)
        print(f"PASS: RideReceipt {receipt.receipt_no} created.")
        print("Check console for receipt email.")
    else:
        print("FAIL: RideReceipt not created.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_full_flow()
