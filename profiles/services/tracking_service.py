import logging
from django.utils import timezone
from flexy_backend.redis_client import redis_geo
from profiles.models import Profile

logger = logging.getLogger(__name__)

class TrackingService:
    @staticmethod
    def update_driver_location(driver_id, lat, lng):
        """
        Updates driver location in both Redis (for real-time) and DB (for persistence).
        """
        try:
            # 1. Update Redis Geospatial Index
            redis_geo.geo_add_driver(driver_id, lat, lng)
            
            # 2. Update DB Profile
            Profile.objects.filter(user_id=driver_id).update(
                last_lat=lat,
                last_lng=lng,
                last_location_update=timezone.now()
            )
            return True
        except Exception as e:
            logger.error(f"TrackingService: Failed to update location for driver {driver_id}: {e}")
            return False

    @staticmethod
    def set_driver_online_status(driver_id, is_online):
        """
        Handles driver status transitions and Redis cleanup.
        """
        try:
            Profile.objects.filter(user_id=driver_id).update(is_online=is_online)
            
            if not is_online:
                # Remove from tracking pool if offline
                redis_geo.geo_remove_driver(driver_id)
            return True
        except Exception as e:
            logger.error(f"TrackingService: Failed to set online status for {driver_id}: {e}")
            return False

    @staticmethod
    def get_online_drivers_count():
        """
        Quick count of online drivers.
        """
        return Profile.objects.filter(is_online=True).count()
