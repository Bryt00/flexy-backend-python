import math
import logging
from datetime import datetime
from core_settings.models import VehicleCategory, DistanceTier

logger = logging.getLogger(__name__)

class PricingService:
    @staticmethod
    def get_surge_multiplier(target_time=None, lat=None, lng=None, radius=5.0):
        """
        Calculates compounded surge multiplier factoring in peak hours and 
        live Redis spatial density.
        """
        multiplier = 1.0

        if target_time is None:
            target_time = datetime.now().time()
            
        peak1_start, peak1_end = datetime.strptime("06:30", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()
        peak2_start, peak2_end = datetime.strptime("16:00", "%H:%M").time(), datetime.strptime("20:00", "%H:%M").time()

        # Step 1: Base Peak Hour Surge
        if (peak1_start <= target_time <= peak1_end) or (peak2_start <= target_time <= peak2_end):
            multiplier = max(multiplier, 1.3)
        
        # Step 2: Dynamic Spatial Demand Surge
        if lat is not None and lng is not None:
            try:
                from flexy_backend.redis_client import redis_geo
                # Query drivers & requests inside radius
                drivers_count = len(redis_geo.geo_radius_drivers(lat, lng, radius))
                requests_count = len(redis_geo.geo_radius_requests(lat, lng, radius))
                
                if requests_count > 0:
                    if drivers_count == 0:
                        # High demand, completely empty pool
                        multiplier = max(multiplier, 2.0)
                    else:
                        ratio = requests_count / float(drivers_count)
                        if ratio >= 3.0:
                            multiplier = max(multiplier, 1.8)
                        elif ratio >= 1.5:
                            multiplier = max(multiplier, 1.5)
            except Exception as e:
                logger.error(f"Error calculating dynamic surge: {e}")

        return multiplier

    @staticmethod
    def calculate_waiting_fee(waiting_minutes):
        """
        Initial flat fee at minute 6 with compound growth.
        """
        if waiting_minutes <= 5:
            return 0.0

        paid_minutes = waiting_minutes - 5
        fee = 2.0 # Initial flat fee
        
        if paid_minutes > 1:
            fee = 2.0 * math.pow(1.002, paid_minutes - 1)
            
        return round(fee, 2)

    @classmethod
    def compute_final_fare(cls, distance_km, vehicle_category_slug, lat=None, lng=None, waiting_minutes=0, payment_method='cash', is_cancelled=False):
        """
        Unified 8-stage fare computation.
        """
        ledger = {
            'base_fare': 0.0,
            'distance_fare': 0.0,
            'waiting_fee': 0.0,
            'cancellation_fee': 0.0,
            'surge_multiplier': 1.0,
            'total_fare': 0.0,
            'driver_payout': 0.0
        }

        try:
            category = VehicleCategory.objects.get(slug=vehicle_category_slug)
        except VehicleCategory.DoesNotExist:
            return ledger

        # 1. Base Fare
        ledger['base_fare'] = float(category.base_fare)

        # 2 & 3. Tiered Distance
        tiers = DistanceTier.objects.filter(is_active=True).order_by('min_km')
        remaining_dist = distance_km
        tiered_dist_charge = 0
        
        for tier in tiers:
            if remaining_dist <= 0: break
            tier_range = tier.max_km - tier.min_km
            dist_in_tier = min(remaining_dist, tier_range)
            scaled_rate = float(tier.rate_per_km) * float(category.multiplier)
            tiered_dist_charge += dist_in_tier * scaled_rate
            remaining_dist -= dist_in_tier

        # 4. Surge (Updated to accept location context)
        ledger['surge_multiplier'] = cls.get_surge_multiplier(lat=lat, lng=lng)
        ledger['distance_fare'] = tiered_dist_charge * ledger['surge_multiplier']

        # 5. Waiting Fee
        ledger['waiting_fee'] = cls.calculate_waiting_fee(waiting_minutes)

        # 6. Cancellation
        if is_cancelled:
            if payment_method.lower() in ['card', 'momo', 'wallet']:
                ledger['cancellation_fee'] = 8.0

        # 7. Final Total
        total = ledger['base_fare'] + ledger['distance_fare'] + ledger['waiting_fee'] + ledger['cancellation_fee']
        ledger['total_fare'] = round(total, 2)

        # 8. Driver Payout (100% logic)
        ledger['driver_payout'] = ledger['total_fare']

        return ledger

    @classmethod
    def calculate_fare_estimates(cls, distance_km, duration_seconds, lat=None, lng=None):
        categories = VehicleCategory.objects.filter(is_active=True)
        estimates = {}
        
        for category in categories:
            ledger = cls.compute_final_fare(distance_km, category.slug, lat=lat, lng=lng)
            estimates[category.slug] = ledger['total_fare']
            
        return estimates
