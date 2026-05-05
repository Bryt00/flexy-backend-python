from celery import shared_task
from django.utils import timezone
from .models import Ride
from profiles.models import Profile
from .services.matching_service import MatchingService
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

@shared_task
def broadcast_heatmap_snapshot():
    from flexy_backend.redis_client import redis_geo
    
    # Global lock with 15s expiry
    if not redis_geo.r.set('heatmap_cron_lock', 'locked', nx=True, ex=15):
        return

    # Efficient retrieval of online drivers location data
    locations = list(Profile.objects.filter(
        is_online=True, 
        last_lat__isnull=False, 
        last_lng__isnull=False
    ).values('user_id', 'last_lat', 'last_lng'))

    data = [
        {
            'driver_id': str(loc['user_id']),
            'latitude': loc['last_lat'],
            'longitude': loc['last_lng']
        } for loc in locations
    ]

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'admin_heatmap',
            {
                'type': 'heatmap_update',
                'data': data
            }
        )
    except Exception as e:
        logger.error(f"Failed to broadcast heatmap: {str(e)}")

    # Reschedule in 10s (Simulating GOLANG Ticker)
    broadcast_heatmap_snapshot.apply_async(countdown=10)


@shared_task(bind=True, max_retries=7)
def process_ride_matching(self, ride_id):
    """
    Orchestrates finding drivers. Retries every 15s for up to 2 minutes until ride is accepted.
    """
    try:
        ride = Ride.objects.get(id=ride_id)
        if ride.status not in ['pending', 'requested']:
            return

        MatchingService.dispatch_ride_request(ride_id)
            
    except Ride.DoesNotExist:
        return
    except Exception as e:
        logger.error(f"Error in process_ride_matching: {e}")
    
    # Always retry every 25s until status changes (accepted/cancelled)
    # Move outside try-except because self.retry() raises a Retry exception
    self.retry(countdown=25)


@shared_task
def cancel_stale_rides():
    limit = timezone.now() - timezone.timedelta(minutes=2)
    Ride.objects.filter(status='pending', created_at__lt=limit).update(status='cancelled')

@shared_task
def activate_scheduled_rides():
    from datetime import timedelta
    now = timezone.now()
    threshold = now + timedelta(minutes=15)
    
    scheduled_rides = Ride.objects.filter(
        is_scheduled=True,
        status='pending',
        scheduled_for__lte=threshold,
        scheduled_for__gte=now - timedelta(minutes=30)
    )
    
    count = 0
    for ride in scheduled_rides:
        process_ride_matching.delay(str(ride.id))
        count += 1
            
    if count > 0:
        logger.info(f"Activated {count} scheduled rides.")

