import math
import logging

logger = logging.getLogger(__name__)

class GeoService:
    @staticmethod
    def calculate_haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculates the great-circle distance between two points
        on the Earth's surface using the Haversine formula.
        Returns distance in meters.
        """
        R = 6371000.0  # Radius of Earth in meters
        
        try:
            ph1 = math.radians(float(lat1))
            ph2 = math.radians(float(lat2))
            d_ph = math.radians(float(lat2) - float(lat1))
            d_lambda = math.radians(float(lon2) - float(lon1))
            
            a = math.sin(d_ph / 2) ** 2 + math.cos(ph1) * math.cos(ph2) * math.sin(d_lambda / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        except (TypeError, ValueError) as e:
            logger.error(f"GeoService: Invalid coordinates provided: {e}")
            return 0.0

    @staticmethod
    def get_compass_heading(lat1, lon1, lat2, lon2):
        """
        Calculates the bearing between two points.
        """
        try:
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_lambda = math.radians(lon2 - lon1)
            
            y = math.sin(delta_lambda) * math.cos(phi2)
            x = math.cos(phi1) * math.sin(phi2) - \
                math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
            
            theta = math.atan2(y, x)
            return (math.degrees(theta) + 360) % 360
        except Exception:
            return 0.0
