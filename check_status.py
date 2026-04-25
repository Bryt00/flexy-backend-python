import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from profiles.models import Profile, DriverVerification
from subscriptions.models import SubscriptionPlan

User = get_user_model()

# Check all users with profiles
users = User.objects.all()
for user in users:
    print(f"\nUser: {user.email}")
    try:
        profile = user.profile
        print(f"  Profile: {profile.full_name} ({profile.user_type})")
        
        if hasattr(profile, 'verification'):
            ver = profile.verification
            print(f"  Verification Status: {ver.status}")
            print(f"  Assigned Category: {ver.assigned_category}")
        else:
            print("  No Verification record found.")
            
        if hasattr(profile, 'subscription'):
            sub = profile.subscription
            print(f"  Subscription Status: {sub.status}")
            print(f"  Expiry: {sub.expiry_date}")
        else:
            print("  No Subscription record found.")
            
    except Exception as e:
        print(f"  Error: {e}")

print("\nAvailable Subscription Plans:")
plans = SubscriptionPlan.objects.all()
for plan in plans:
    print(f"  - {plan.name} ({plan.category}): GH₵ {plan.price}")
