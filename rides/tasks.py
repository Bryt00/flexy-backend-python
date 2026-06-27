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

    # Compress payload by reducing float precision to 4 decimal places (11m accuracy)
    # and capping the max markers to 500 to prevent WebSocket bloat.
    data = [
        {
            'driver_id': str(loc['user_id']),
            'latitude': round(loc['last_lat'], 4),
            'longitude': round(loc['last_lng'], 4)
        } for loc in locations[:500]
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
        from flexy_backend.redis_client import redis_geo
        lock_key = f"matching_lock:{ride_id}"
        
        # 20s lock to ensure only one task runs per dispatch window
        if not redis_geo.r.set(lock_key, "locked", nx=True, ex=20):
            logger.info(f"Matching: Task for ride {ride_id} already in progress. Skipping.")
            return

        ride = Ride.objects.get(id=ride_id)
        if ride.status not in ['pending', 'requested']:
            # Remove from Redis surge index if no longer pending
            redis_geo.geo_remove_request(ride_id)
            return

        # Add to surge index for the current cycle
        redis_geo.geo_add_request(ride_id, ride.pickup_lat, ride.pickup_lng)

        MatchingService.dispatch_ride_request(ride_id)
            
    except Ride.DoesNotExist:
        redis_geo.geo_remove_request(ride_id)
        return
    except Exception as e:
        logger.error(f"Error in process_ride_matching: {e}")
    
    # Retry every 10s (reduced from 25s for better responsiveness)
    self.retry(countdown=10)


@shared_task
def cancel_stale_rides():
    from django.db.models import Q
    limit = timezone.now() - timezone.timedelta(minutes=2)
    # Ensure we don't accidentally cancel scheduled rides that are waiting for their scheduled time
    Ride.objects.filter(
        Q(is_scheduled=False) | Q(is_scheduled__isnull=True),
        status='pending', 
        created_at__lt=limit
    ).update(status='cancelled')

@shared_task
def cancel_abandoned_rides():
    """
    Cancels rides that have been stuck in an active state for over 3 minutes.
    This prevents users from resuming ancient rides upon login.
    """
    limit = timezone.now() - timezone.timedelta(minutes=3)
    abandoned_rides = Ride.objects.filter(
        status__in=['accepted', 'arrived', 'in_progress'],
        updated_at__lt=limit
    )
    count = abandoned_rides.update(status='cancelled')
    if count > 0:
        logger.info(f"Cleanup: Cancelled {count} abandoned active rides older than 3 minutes.")

@shared_task
def cancel_stale_deliveries():
    """
    Cancels courier deliveries that have been pending for more than 2 minutes
    without being accepted by any rider/driver.
    """
    from courier.models import Delivery
    from courier.serializers import DeliverySerializer
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    limit = timezone.now() - timezone.timedelta(minutes=2)
    stale_deliveries = Delivery.objects.filter(status='PENDING', created_at__lt=limit)
    
    if stale_deliveries.exists():
        channel_layer = get_channel_layer()
        for delivery in stale_deliveries:
            delivery.status = 'CANCELLED'
            delivery.save()
            logger.info(f"Courier: Stale delivery {delivery.id} timed out and was cancelled automatically.")
            
            # Broadcast status update to the passenger
            async_to_sync(channel_layer.group_send)(
                f'delivery_{delivery.id}',
                {
                    'type': 'delivery_broadcast',
                    'message_type': 'status_update',
                    'data': DeliverySerializer(delivery).data
                }
            )
            
            # Broadcast removal from discovery stream for all drivers
            async_to_sync(channel_layer.group_send)(
                'delivery_discovery',
                {
                    'type': 'delivery_broadcast',
                    'message_type': 'delivery_taken',
                    'data': {'delivery_id': str(delivery.id)}
                }
            )

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
    
    # 2. Cleanup: Cancel rides that are more than 30 minutes overdue and never got matched
    overdue_rides = Ride.objects.filter(
        is_scheduled=True,
        status='pending',
        scheduled_for__lt=now - timedelta(minutes=30)
    )
    overdue_count = overdue_rides.update(status='cancelled')
    if overdue_count > 0:
        logger.info(f"Cleanup: Cancelled {overdue_count} overdue scheduled rides.")

    # 3. Activation: Trigger matching for upcoming rides
    count = 0
    for ride in scheduled_rides:
        process_ride_matching.delay(str(ride.id))
        count += 1
            
    if count > 0:
        logger.info(f"Triggered dispatch for {count} scheduled rides.")

@shared_task
def remind_upcoming_scheduled_rides():
    from datetime import timedelta
    from notification.utils import send_notification
    
    now = timezone.now()
    target_time_start = now + timedelta(minutes=29)
    target_time_end = now + timedelta(minutes=31)
    
    # Find rides that are accepted and are about 30 mins away
    upcoming_rides = Ride.objects.filter(
        is_scheduled=True,
        status='accepted',
        driver__isnull=False,
        scheduled_for__gte=target_time_start,
        scheduled_for__lte=target_time_end
    )
    
    count = 0
    for ride in upcoming_rides:
        # Check if reminder already sent to prevent duplicate pushes (if we ran multiple times in the window)
        # Use a simple metadata flag or redis key
        from flexy_backend.redis_client import redis_geo
        lock_key = f"ride_reminder_sent:{ride.id}"
        if redis_geo.r.set(lock_key, "1", nx=True, ex=3600):
            send_notification(
                ride.driver,
                title="Upcoming Scheduled Ride",
                body=f"Reminder: You have a scheduled ride from {ride.pickup_address} starting in about 30 minutes.",
                type='PUSH',
                ref_id=ride.id,
                save_in_db=False
            )
            count += 1
            
    if count > 0:
        logger.info(f"Sent {count} reminders for upcoming scheduled rides.")

@shared_task
def check_single_ride_anomaly(ride_id):
    from .services.safety_service import SafetyService
    if SafetyService.check_ride_anomaly(ride_id):
        logger.info(f"Safety: Anomaly detected for ride {ride_id}.")

@shared_task
def monitor_active_rides_safety():
    """
    Scans all 'in_progress' rides and dispatches anomaly checks.
    Runs every 60s via celery-beat.
    """
    active_ride_ids = Ride.objects.filter(status='in_progress').values_list('id', flat=True)
    count = 0
    for ride_id in active_ride_ids:
        check_single_ride_anomaly.delay(str(ride_id))
        count += 1
    
    if count > 0:
        logger.info(f"Safety: Dispatched anomaly checks for {count} active rides.")

