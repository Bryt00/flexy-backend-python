from core_settings.models import VehicleCategory, DistanceTier
from datetime import datetime
import logging
import math

logger = logging.getLogger(__name__)

class FareCalculator:
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
        Stage 5: Waiting Fee Logic (Screenshot 4)
        - First 5 mins: FREE
        - After 5 mins: Flat GHS 2 + 0.2% compound growth per minute on the fee itself.
        """
        if waiting_minutes <= 5:
            return 0.0

        paid_minutes = waiting_minutes - 5
        fee = 2.0 # Initial flat fee at minute 6
        
        # Compound growth of 0.2% per minute
        # Formula for compound growth: A = P(1 + r)^n
        # Here P=2, r=0.002, n=paid_minutes-1 (since flat 2 is for the first paid min)
        if paid_minutes > 1:
            fee = 2.0 * math.pow(1.002, paid_minutes - 1)
            
        return round(fee, 2)

    @staticmethod
    def compute_final_fare(distance_km, vehicle_category_slug, waiting_minutes=0, payment_method='cash', is_cancelled=False):
        """
        Final Fare Calculation Sequence (8 Stages - Screenshot 7)
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
            logger.error(f"Category {vehicle_category_slug} not found.")
            return ledger

        # Stage 1: Add Base Fare
        ledger['base_fare'] = category.base_fare

        # Stage 2 & 3: Add Tiered Distance Charges + Category Multiplier
        tiers = DistanceTier.objects.filter(is_active=True).order_by('min_km')
        remaining_dist = distance_km
        tiered_dist_charge = 0
        
        for tier in tiers:
            if remaining_dist <= 0: break
            tier_range = tier.max_km - tier.min_km
            dist_in_tier = min(remaining_dist, tier_range)
            
            # (Stage 2) Tier Rate * (Stage 3) Category Multiplier
            scaled_rate = tier.rate_per_km * category.multiplier
            tiered_dist_charge += dist_in_tier * scaled_rate
            remaining_dist -= dist_in_tier

        # Stage 4: Apply Surge Multiplier (To km-based charges only)
        ledger['surge_multiplier'] = FareCalculator.get_surge_multiplier()
        ledger['distance_fare'] = tiered_dist_charge * ledger['surge_multiplier']

        # Stage 5: Add Waiting Fee
        ledger['waiting_fee'] = FareCalculator.calculate_waiting_fee(waiting_minutes)

        # Stage 6: Apply Cancellation Logic
        if is_cancelled:
            # GHS 8 fee only for card/momo
            if payment_method.lower() in ['card', 'momo', 'wallet']:
                ledger['cancellation_fee'] = 8.0
            else:
                ledger['cancellation_fee'] = 0.0

        # Stage 7: Format Final Amount
        total = ledger['base_fare'] + ledger['distance_fare'] + ledger['waiting_fee'] + ledger['cancellation_fee']
        ledger['total_fare'] = round(total, 2)

        # Stage 8: Payout Assignment (100% to driver)
        ledger['driver_payout'] = ledger['total_fare']

        return ledger

    @staticmethod
    def calculate_fare_estimates(distance_km, duration_seconds):
        """
        Provides estimates for all active categories (Simplified 8-stage).
        """
        categories = VehicleCategory.objects.filter(is_active=True)
        estimates = {}
        
        for category in categories:
            ledger = FareCalculator.compute_final_fare(distance_km, category.slug)
            estimates[category.slug] = ledger['total_fare']
            
        return estimates

class GeospatialUtils:
    @staticmethod
    def calculate_haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculates the great-circle distance between two points
        on the Earth's surface using the Haversine formula.
        Returns distance in meters.
        """
        R = 6371000.0  # Radius of Earth in meters
        
        ph1 = math.radians(lat1)
        ph2 = math.radians(lat2)
        d_ph = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(d_ph / 2) ** 2 + math.cos(ph1) * math.cos(ph2) * math.sin(d_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

