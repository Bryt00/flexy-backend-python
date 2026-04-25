
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from django.utils import timezone
from profiles.models import Profile
from rides.models import Ride
from rides.services.matching_service import MatchingService
from django.contrib.auth import get_user_model

# Configure logging to capture to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('rides.services.matching_service')

User = get_user_model()

def run_simulation():
    print("--- Starting Matching Simulation ---")
    
    # 1. Update test driver
    try:
        u = User.objects.get(email='test@drive.com')
        p = Profile.objects.get(user=u)
        p.last_location_update = timezone.now()
        # Set a clear location for testing (Accra Mall area)
        p.last_lat = 5.6200
        p.last_lng = -0.1700
        p.is_online = True
        p.save()
        
        # Ensure vehicle is ready
        v = p.user.vehicles.first()
        if v:
            v.is_active = True
            v.is_verified = True
            v.save()
            print(f"Driver {u.email} updated. Vehicle type: {v.type}")
            
        # 2. Add to Redis manually to guarantee pool entry
        from flexy_backend.redis_client import redis_geo
        redis_geo.geo_add_driver(str(p.pk), p.last_lat, p.last_lng)
        
        # 3. Create a dummy ride request nearby
        ride = Ride.objects.create(
            rider=User.objects.filter(role='rider').first(),
            pickup_lat=5.6205, # Very close
            pickup_lng=-0.1705,
            dropoff_lat=5.6500,
            dropoff_lng=-0.1500,
            pickup_address="Testing Ground",
            dropoff_address="Destination X",
            preferred_vehicle_type='go', # Test the category mismatch
            status='pending',
            fare=25.0
        )
        print(f"Created Ride {ride.id} with category '{ride.preferred_vehicle_type}'")
        
        # 4. Run Matching
        print("Dispatching...")
        count = MatchingService.dispatch_ride_request(ride.id)
        print(f"Simulation Result: Dispatched to {count} drivers.")
        
        # 5. Cleanup
        ride.delete()
        
    except Exception as e:
        print(f"Simulation Failed: {e}")

if __name__ == "__main__":
    run_simulation()
