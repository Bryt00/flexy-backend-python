from celery import shared_task
from django.utils import timezone
from .models import Ride
from profiles.models import Profile
import math

def haversine(lat1, lon1, lat2, lon2):
    # Simplified haversine distance in km
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@shared_task
def process_ride_matching(ride_id):
    try:
        ride = Ride.objects.get(id=ride_id)
        if ride.status != 'pending':
            return
        
        # Simple Logic: Find nearest verified online drivers in profiles
        # In a production monolithic Django app, we might use PostGIS or a 
        # simpler spatial query if not using PostGIS.
        # Since we switched to FloatField for local stability:
        
        available_drivers = Profile.objects.filter(
            user__role='driver',
            verification__is_verified=True
        )
        
        # Filtering for drivers within 5km of pickup
        for driver in available_drivers:
            # We assume driver location is stored in another model or on Profile
            # For MVP, we'll just log the attempt
            pass
            
        print(f"Task: Matching ride {ride_id} with available drivers...")
    except Ride.DoesNotExist:
        pass

@shared_task
def cancel_stale_rides():
    # Cleanup task for rides pending for > 15 mins
    limit = timezone.now() - timezone.timedelta(minutes=15)
    Ride.objects.filter(status='pending', created_at__lt=limit).update(status='cancelled')
