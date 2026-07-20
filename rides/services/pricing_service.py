import logging
from rides.utils import FareCalculator

logger = logging.getLogger(__name__)

class PricingService:
    @staticmethod
    def get_surge_multiplier(lat=None, lng=None, radius=5.0):
        """
        Proxies to FareCalculator but allows for service-layer overrides or logging.
        """
        return FareCalculator.get_surge_multiplier(lat=lat, lng=lng, radius=radius)

    @staticmethod
    def calculate_fare_estimates(dist_km, duration_sec, lat=None, lng=None, d_lat=None, d_lng=None, num_stops=0, duration_in_traffic_sec=None):
        """
        Calculates fare estimates for all active vehicle categories.
        """
        from core_settings.models import VehicleCategory
        from django.contrib.gis.geos import Point
        
        categories = VehicleCategory.objects.filter(is_active=True)
        estimates = {}
        
        pickup_point = Point(float(lng), float(lat), srid=4326) if lat and lng else None
        dropoff_point = Point(float(d_lng), float(d_lat), srid=4326) if d_lat and d_lng else None
        
        # Calculate global surge once for this estimate request
        surge = FareCalculator.get_surge_multiplier(
            lat=lat, lng=lng,
            duration_seconds=duration_sec,
            duration_in_traffic=duration_in_traffic_sec
        )
        
        for category in categories:
            if not category.is_passenger_allowed:
                # If it's a restricted vehicle (e.g. e-bike), check geofence exceptions
                if not pickup_point or not dropoff_point:
                    continue
                
                allowed_areas = category.allowed_service_areas.all()
                if not allowed_areas:
                    continue
                
                pickup_allowed = False
                dropoff_allowed = False
                for area in allowed_areas:
                    if area.polygon.contains(pickup_point):
                        pickup_allowed = True
                    if area.polygon.contains(dropoff_point):
                        dropoff_allowed = True
                    if pickup_allowed and dropoff_allowed:
                        break
                        
                if not (pickup_allowed and dropoff_allowed):
                    continue
                    
            ledger = FareCalculator.compute_final_fare(
                dist_km, 
                category.slug, 
                surge_override=surge,
                num_stops=num_stops,
                lat=lat,
                lng=lng
            )
            estimates[category.slug] = ledger['total_fare']
            
        return estimates

    @staticmethod
    def compute_final_fare(distance_km, vehicle_category_slug, lat=None, lng=None, waiting_minutes=0, payment_method='cash', num_stops=0):
        """
        Computes the final 8-stage pricing ledger for a completed ride.
        """
        # Calculate live surge at the point of completion (or pickup)
        surge = FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        
        return FareCalculator.compute_final_fare(
            distance_km=distance_km,
            vehicle_category_slug=vehicle_category_slug,
            waiting_minutes=waiting_minutes,
            payment_method=payment_method,
            surge_override=surge,
            num_stops=num_stops,
            lat=lat,
            lng=lng
        )
