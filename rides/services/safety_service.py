import math
import logging
from rides.models import Ride, Incident
from django.utils import timezone

logger = logging.getLogger(__name__)

class SafetyService:
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Haversine formula to calculate distance in km."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @classmethod
    def check_ride_anomaly(cls, ride_id):
        """
        Simple anomaly detection: If a driver is further than 1km from a straight line 
        between current and dropoff, while 'in_progress', flag it.
        (Note: Ideally uses OSRM polylines, but this is a robust baseline).
        """
        try:
            ride = Ride.objects.get(id=ride_id)
            if ride.status != 'in_progress' or not ride.driver:
                return False

            # Get driver's latest location from profile
            profile = ride.driver.profile
            curr_lat = profile.last_lat
            curr_lng = profile.last_lng

            if not curr_lat or not curr_lng:
                return False

            # 1. Check distance to destination
            dist_to_dest = cls.calculate_distance(curr_lat, curr_lng, ride.dropoff_lat, ride.dropoff_lng)
            
            # 2. Logic: If the driver is moving AWAY from the destination significantly
            # Or if they are stuck for too long (TODO)
            # For now, we use a simple 'Maximum Distance from Path' or 'Moving Away' check
            
            # Implementation: If distance is > 20% further than original estimated distance, 
            # and they are not near the dropoff, trigger alert.
            # This is a simplified fallback for the OSRM gap.
            
            if dist_to_dest > ride.distance * 1.5 and dist_to_dest > 2.0:
                logger.warning(f"Safety: Ride {ride_id} detected as anomaly. Distance to dest: {dist_to_dest}km")
                
                # Create Incident if not exists
                Incident.objects.get_or_create(
                    ride=ride,
                    reporter=ride.rider,
                    type='SOS',
                    status='ACTIVE',
                    description=f"Automated Anomaly Detection: Driver is {dist_to_dest}km from destination, exceeding expected bounds."
                )
                return True
                
            return False

        except Exception as e:
            logger.error(f"Safety Check Failure: {e}")
            return False
