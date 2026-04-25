import os
import django
import time
from django.utils import timezone
from datetime import timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from rides.models import Ride
from profiles.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

def verify_tracking():
    print("--- Verifying Tracking & Throttling Logic ---")
    
    # 1. Setup Test Data
    user, _ = User.objects.get_or_create(email='test_track@track.com')
    profile, _ = Profile.objects.get_or_create(user=user, full_name='Tester Driver')
    
    ride = Ride.objects.create(
        rider=user,
        pickup_lat=6.039, pickup_lng=-0.278,
        dropoff_lat=6.066, dropoff_lng=-0.267,
        status='accepted',
        driver=user,
        preferred_vehicle_type='go'
    )
    print(f"Created Ride {ride.id}")

    # 2. First Track (No previous state)
    # Expected: Google API call (Simulation)
    from django.test import RequestFactory
    from rest_framework.test import force_authenticate
    from rides.views import RideViewSet
    
    factory = RequestFactory()
    view = RideViewSet.as_view({'post': 'track'})
    
    data = {'lat': 6.0391, 'lng': -0.2782}
    request = factory.post(f'/v1/rides/{ride.id}/track/', data, content_type='application/json')
    force_authenticate(request, user=user)
    
    print("\n[CALL 1: Initial Location]")
    response = view(request, pk=str(ride.id))
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    ride.refresh_from_db()
    
    update1_time = ride.last_tracking_time
    print(f"Update 1 Time: {update1_time}")
    print(f"Distance Remaining: {ride.distance_remaining} km")

    # 3. Second Track (Immediate, exact same location)
    # Expected: No Google API update (Throttled)
    print("\n[CALL 2: Immediate Duplicate (Same Loc)]")
    request = factory.post(f'/v1/rides/{ride.id}/track/', data, content_type='application/json')
    force_authenticate(request, user=user)
    response = view(request, pk=str(ride.id))
    ride.refresh_from_db()
    print(f"Update 2 Time: {ride.last_tracking_time} (Expected to match Update 1)")
    
    if ride.last_tracking_time == update1_time:
        print("PASS: Throttling working correctly for time/distance.")
    else:
        print("FAIL: Throttling failed.")

    # 4. Third Track (Significant movement > 200m)
    # 0.002 lat shift is roughly 222 meters
    print("\n[CALL 3: Significant Movement (>200m)]")
    data = {'lat': 6.0411, 'lng': -0.2782}
    request = factory.post(f'/v1/rides/{ride.id}/track/', data, content_type='application/json')
    force_authenticate(request, user=user)
    response = view(request, pk=str(ride.id))
    ride.refresh_from_db()

    
    if ride.last_tracking_time > update1_time:
        print(f"PASS: Updated due to movement. New Time: {ride.last_tracking_time}")
    else:
        print("FAIL: Significant movement did not trigger update.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_tracking()
