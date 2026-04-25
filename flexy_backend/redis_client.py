import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RedisGeoClient:
    def __init__(self):
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.r = redis.Redis.from_url(redis_url, decode_responses=True)
        self.location_key = "driver_locations"

    def geo_add_driver(self, driver_id, lat, lng):
        """
        Adds or updates a driver's location in the Redis Geo set.
        Returns the number of elements added (1 if new, 0 if updated).
        """
        try:
            # using raw execute_command to ensure the correct Redis protocol is used regardless of library version
            return self.r.execute_command('GEOADD', self.location_key, float(lng), float(lat), str(driver_id))
        except Exception as e:
            logger.error(f"Failed to add driver to Redis geo index: {str(e)}")
            return 0

    def geo_radius_drivers(self, lat, lng, radius_km):
        """
        Retrieves all driver_ids within the specified radius (in km).
        Returns a list of driver_ids.
        """
        try:
            # georadius(name, longitude, latitude, radius, unit='m')
            # returns list of members
            results = self.r.georadius(self.location_key, float(lng), float(lat), float(radius_km), unit='km')
            return [str(res) for res in results]
        except Exception as e:
            logger.error(f"Failed to query georadius: {str(e)}")
            return []

    def geo_radius_drivers_with_dist(self, lat, lng, radius_km):
        """
        Retrieves all driver_ids within the specified radius with distance.
        Returns a list of tuples (driver_id, distance).
        """
        try:
            results = self.r.georadius(self.location_key, float(lng), float(lat), float(radius_km), unit='km', withdist=True)
            # results is a list of [member, distance]
            return [(str(res[0]), float(res[1])) for res in results]
        except Exception as e:
            logger.error(f"Failed to query georadius with dist: {str(e)}")
            return []

    def get_driver_positions(self, driver_ids):
        """
        Retrieves the [lng, lat] for a list of driver_ids.
        Returns a dictionary mapping driver_id to [longitude, latitude].
        """
        if not driver_ids:
            return {}
        try:
            # GEOPOS key member [member...]
            positions = self.r.geopos(self.location_key, *driver_ids)
            return {driver_ids[i]: pos for i, pos in enumerate(positions) if pos}
        except Exception as e:
            logger.error(f"Failed to fetch geopos for drivers: {e}")
            return {}

    def geo_remove_driver(self, driver_id):
        """
        Removes a driver from the active tracking pool.
        """
        try:
            return self.r.zrem(self.location_key, str(driver_id))
        except Exception as e:
            logger.error(f"Failed to remove driver from Redis: {str(e)}")
            return 0

    def set_driver_lock(self, driver_id, duration=15):
        """
        Locks a driver for a specific duration to prevent concurrent ride dispatches.
        """
        try:
            key = f"driver_lock:{driver_id}"
            return self.r.set(key, "locked", ex=duration)
        except Exception as e:
            logger.error(f"Failed to set driver lock: {e}")
            return False

    def is_driver_locked(self, driver_id):
        """
        Checks if a driver is currently locked.
        """
        try:
            return self.r.exists(f"driver_lock:{driver_id}")
        except Exception as e:
            logger.error(f"Failed to check driver lock: {e}")
            return False

    def geo_add_request(self, ride_id, lat, lng):
        """
        Adds a passenger's active ride request to the Redis Geo Index for surge calculation.
        """
        try:
            return self.r.geoadd('ride_requests', [float(lng), float(lat), str(ride_id)])
        except Exception as e:
            logger.error(f"Failed to add request to Redis geo index: {str(e)}")
            return 0

    def geo_radius_requests(self, lat, lng, radius_km):
        """
        Retrieves all active ride requests within the specified radius to calculate surge density.
        """
        try:
            results = self.r.georadius('ride_requests', float(lng), float(lat), float(radius_km), unit='km')
            return [str(res) for res in results]
        except Exception as e:
            logger.error(f"Failed to query georadius requests: {str(e)}")
            return []

    def geo_remove_request(self, ride_id):
        """
        Removes an active ride request once assigned.
        """
        try:
            return self.r.zrem('ride_requests', str(ride_id))
        except Exception as e:
            logger.error(f"Failed to remove request from Redis: {str(e)}")
            return 0

# Singleton instance for project-wide usage
redis_geo = RedisGeoClient()
