import os
import django
import sys

# Setup django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from rides.models import Ride
from rides.services.matching_service import MatchingService

def run_test():
    # Create a dummy ride in a remote location (0,0) where no drivers are likely to be
    ride = Ride.objects.create(status='pending', pickup_lat=0, pickup_lng=0)
    print(f"Created Test Ride: {ride.id}")
    
    try:
        for i in range(3):
            print(f"\n--- Attempt {i} ---")
            count = MatchingService.dispatch_ride_request(str(ride.id))
            ride.refresh_from_db()
            metadata = ride.dispatch_metadata
            attempt_count = metadata.get('attempt_count', 0)
            # Next radius will be based on this attempt_count
            print(f"Dispatched to {count} drivers.")
            print(f"Updated Metadata: {metadata}")
            
    finally:
        # Cleanup
        ride.delete()
        print("\nTest Ride deleted.")

if __name__ == "__main__":
    run_test()
