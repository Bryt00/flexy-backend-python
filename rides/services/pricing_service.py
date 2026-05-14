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
    def calculate_fare_estimates(dist_km, duration_sec, lat=None, lng=None, num_stops=0):
        """
        Calculates fare estimates for all active vehicle categories.
        """
        from core_settings.models import VehicleCategory
        categories = VehicleCategory.objects.filter(is_active=True)
        estimates = {}
        
        # Calculate global surge once for this estimate request
        surge = FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        
        for category in categories:
            ledger = FareCalculator.compute_final_fare(
                dist_km, 
                category.slug, 
                surge_override=surge,
                num_stops=num_stops
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
            num_stops=num_stops
        )
