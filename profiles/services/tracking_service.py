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
        Handles driver status transitions, Vehicle status sync, and Redis cleanup.
        """
        try:
            # 1. Update Profile Online Status
            Profile.objects.filter(user_id=driver_id).update(
                is_online=is_online, 
                last_location_update=timezone.now()
            )
            
            # 2. Sync Vehicle Status (Available vs Offline)
            from vehicles.models import Vehicle
            target_status = 'available' if is_online else 'offline'
            
            # Only update if not currently 'riding' to avoid disrupting active trips
            Vehicle.objects.filter(driver_id=driver_id, is_active=True).exclude(status='riding').update(status=target_status)
            
            # 3. Redis Synchronization
            if is_online:
                profile = Profile.objects.filter(user_id=driver_id).first()
                if profile and profile.last_lat and profile.last_lng:
                    redis_geo.geo_add_driver(driver_id, profile.last_lat, profile.last_lng)
            else:
                # Remove from tracking pool if offline
                redis_geo.geo_remove_driver(driver_id)
            return True
        except Exception as e:
            logger.error(f"TrackingService: Failed to set online status for {driver_id}: {e}")
            return False

    @staticmethod
    def set_driver_ride_status(driver_id, is_riding):
        """
        Updates vehicle status to 'riding' or back to 'available'/'offline' based on profile state.
        """
        try:
            from vehicles.models import Vehicle
            if is_riding:
                Vehicle.objects.filter(driver_id=driver_id, is_active=True).update(status='riding')
            else:
                profile = Profile.objects.filter(user_id=driver_id).first()
                target_status = 'available' if profile and profile.is_online else 'offline'
                Vehicle.objects.filter(driver_id=driver_id, is_active=True).update(status=target_status)
            return True
        except Exception as e:
            logger.error(f"TrackingService: Failed to set ride status for {driver_id}: {e}")
            return False

    @staticmethod
    def get_online_drivers_count():
        """
        Quick count of online drivers.
        """
        return Profile.objects.filter(is_online=True).count()
