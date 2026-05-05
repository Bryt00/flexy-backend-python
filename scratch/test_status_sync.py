import os
import django
import sys

# Setup django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from profiles.models import Profile
from vehicles.models import Vehicle
from profiles.services.tracking_service import TrackingService

def run_test():
    # Find a driver profile and their vehicle
    profile = Profile.objects.filter(user__role='driver').first()
    if not profile:
        print("No driver profile found for testing.")
        return

    # Ensure a vehicle exists
    vehicle, _ = Vehicle.objects.get_or_create(driver=profile, defaults={'is_active': True, 'is_verified': True})
    vehicle.is_active = True
    vehicle.is_verified = True
    vehicle.status = 'offline'
    vehicle.save()

    print(f"Testing status sync for Driver {profile.pk}")
    print(f"Initial State: Profile Online={profile.is_online}, Vehicle Status={vehicle.status}")

    # 1. Go Online
    print("\n--- Going Online ---")
    TrackingService.set_driver_online_status(str(profile.pk), True)
    profile.refresh_from_db()
    vehicle.refresh_from_db()
    print(f"Result: Profile Online={profile.is_online}, Vehicle Status={vehicle.status}")

    # 2. Start Ride (Simulate)
    print("\n--- Starting Ride ---")
    TrackingService.set_driver_ride_status(str(profile.pk), True)
    vehicle.refresh_from_db()
    print(f"Result: Vehicle Status={vehicle.status}")

    # 3. Complete Ride
    print("\n--- Completing Ride ---")
    TrackingService.set_driver_ride_status(str(profile.pk), False)
    vehicle.refresh_from_db()
    print(f"Result: Vehicle Status={vehicle.status} (should be available)")

    # 4. Go Offline
    print("\n--- Going Offline ---")
    TrackingService.set_driver_online_status(str(profile.pk), False)
    profile.refresh_from_db()
    vehicle.refresh_from_db()
    print(f"Result: Profile Online={profile.is_online}, Vehicle Status={vehicle.status}")

if __name__ == "__main__":
    run_test()
