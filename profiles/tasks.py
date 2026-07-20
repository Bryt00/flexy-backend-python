import json
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from flexy_backend.redis_client import redis_geo
from profiles.models import Profile

logger = logging.getLogger(__name__)

@shared_task
def flush_driver_locations_to_db(batch_size=1000):
    """
    Pops queued driver location updates from Redis, deduplicates them,
    and bulk writes them to the PostgreSQL database.
    """
    try:
        # 1. Pop location updates from the Redis list
        raw_updates = redis_geo.pop_driver_location_updates(batch_size=batch_size)
        if not raw_updates:
            return 0

        # 2. Parse and keep only the latest location per driver_id (deduplication)
        latest_updates = {}
        for raw in raw_updates:
            try:
                data = json.loads(raw)
                driver_id = data.get('driver_id')
                lat = data.get('lat')
                lng = data.get('lng')
                timestamp = data.get('timestamp')
                
                if not driver_id or lat is None or lng is None:
                    continue
                
                existing = latest_updates.get(driver_id)
                if not existing or timestamp > existing['timestamp']:
                    latest_updates[driver_id] = {
                        'lat': lat,
                        'lng': lng,
                        'timestamp': timestamp
                    }
            except Exception as parse_err:
                logger.error(f"Error parsing driver location data: {parse_err}")

        if not latest_updates:
            return 0

        # 3. Perform bulk update inside a transaction
        updated_count = 0
        with transaction.atomic():
            for driver_id, loc in latest_updates.items():
                Profile.objects.filter(user_id=driver_id).update(
                    last_lat=loc['lat'],
                    last_lng=loc['lng'],
                    last_location_update=timezone.now()
                )
                updated_count += 1
                
        logger.info(f"Write-Behind: Successfully flushed {updated_count} driver location updates to DB.")
        return updated_count
    except Exception as e:
        logger.error(f"Error in flush_driver_locations_to_db: {e}")
        return 0
