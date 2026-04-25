import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from profiles.models import Profile, DriverVerification
from subscriptions.models import SubscriptionPlan
from vehicles.models import Vehicle

User = get_user_model()

# 1. Create Subscription Plans
plans_data = [
    ('Flexy Go Monthly', 'go', 100),
    ('Flexy Comfort Monthly', 'comfort', 150),
    ('Flexy XL Monthly', 'xl', 200),
    ('Flexy Executive Monthly', 'exec', 300),
    ('Flexy Pragya Monthly', 'pragya', 50),
]

for name, category, price in plans_data:
    plan, created = SubscriptionPlan.objects.get_or_create(
        category=category,
        defaults={'name': name, 'price': price, 'duration_days': 30, 'is_active': True}
    )
    if created:
        print(f"Created plan: {name}")
    else:
        # Update existing plan just in case
        plan.name = name
        plan.price = price
        plan.save()
        print(f"Updated plan: {name}")

# 2. Setup Test User (test@drive.com)
user = User.objects.filter(email='test@drive.com').first()
if user:
    profile, _ = Profile.objects.get_or_create(user=user)
    verification, _ = DriverVerification.objects.get_or_create(driver=profile)
    
    # Assign to Go category so they can see the Go plan
    verification.assigned_category = 'go'
    verification.status = 'VERIFIED'
    verification.is_verified = True
    verification.save()

    # 3. Setup Test Vehicle for "Current Vehicle" display
    Vehicle.objects.get_or_create(
        driver=profile,
        license_plate='GW-772-24',
        defaults={
            'make': 'Toyota',
            'model': 'Corolla',
            'year': 2022,
            'color': 'Midnight Blue',
            'type': 'go',
            'status': 'available',
            'is_active': True,
            'is_verified': True
        }
    )
    
    # 4. Setup Loyalty Status for "FlexyPro"
    profile.points = 1250
    profile.tier = 'Gold'
    profile.acceptance_rate = 98.5
    profile.total_rides = 450
    profile.save()

    print(f"Updated test@drive.com: Assigned to 'go' category, VERIFIED, added Vehicle, and set Loyalty points (1250).")
else:
    print("User test@drive.com not found. Please log in with a valid driver account.")
