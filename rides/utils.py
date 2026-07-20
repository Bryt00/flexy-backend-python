from core_settings.models import VehicleCategory, DistanceTier
from datetime import datetime
import logging
import math

logger = logging.getLogger(__name__)

class FareCalculator:
    @staticmethod
    def _get_active_categories():
        from django.core.cache import cache
        cache_key = "active_vehicle_categories_list"
        try:
            categories = cache.get(cache_key)
            if categories is not None:
                return categories
        except Exception:
            pass
        
        categories = list(VehicleCategory.objects.filter(is_active=True))
        try:
            cache.set(cache_key, categories, timeout=300)
        except Exception:
            pass
        return categories

    @staticmethod
    def _get_active_distance_tiers():
        from django.core.cache import cache
        cache_key = "active_distance_tiers_list"
        try:
            tiers = cache.get(cache_key)
            if tiers is not None:
                return tiers
        except Exception:
            pass
        
        tiers = list(DistanceTier.objects.filter(is_active=True).order_by('min_km'))
        try:
            cache.set(cache_key, tiers, timeout=300)
        except Exception:
            pass
        return tiers

    @staticmethod
    def _get_active_pricing_rules():
        from django.core.cache import cache
        cache_key = "active_pricing_rules_list"
        try:
            rules = cache.get(cache_key)
            if rules is not None:
                return rules
        except Exception:
            pass
        
        from core_settings.models import PricingRule
        rules = list(PricingRule.objects.filter(is_active=True).select_related('city'))
        try:
            cache.set(cache_key, rules, timeout=300)
        except Exception:
            pass
        return rules

    @staticmethod
    def get_surge_multiplier(target_time=None, lat=None, lng=None, radius=5.0, duration_seconds=None, duration_in_traffic=None):
        """
        Calculates compounded surge multiplier factoring in admin-set rules, 
        peak hours, live Redis spatial density, traffic delays, and weather.
        """
        from integrations.weather import WeatherService
        multiplier = 1.0
        
        enable_weather = True
        max_weather = 1.5
        enable_traffic = True
        max_traffic = 1.5

        # Step 1: Admin-set Pricing Rule (Manual Surge & Toggles)
        try:
            rule = None
            rules = FareCalculator._get_active_pricing_rules()
            if lat is not None and lng is not None:
                min_dist = float('inf')
                for r in rules:
                    if r.city and r.city.is_active and r.city.latitude is not None and r.city.longitude is not None:
                        dist = GeospatialUtils.calculate_haversine_distance(lat, lng, r.city.latitude, r.city.longitude) / 1000.0
                        if dist < 100.0 and dist < min_dist:
                            min_dist = dist
                            rule = r
            
            if not rule:
                rule = next((r for r in rules if r.city is None), None)
                if not rule and rules:
                    rule = rules[0]

            if rule:
                enable_weather = rule.enable_weather_surge
                max_weather = rule.max_weather_surge
                enable_traffic = rule.enable_traffic_surge
                max_traffic = rule.max_traffic_surge
                
                raw_surge = rule.surge_multiplier
                if raw_surge > 3.0:
                    scaled_surge = raw_surge / 10.0
                else:
                    scaled_surge = raw_surge
                multiplier = max(multiplier, scaled_surge)
        except Exception as e:
            logger.error(f"Error fetching PricingRule: {e}")

        if target_time is None:
            target_time = datetime.now().time()
            
        peak1_start, peak1_end = datetime.strptime("06:30", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()
        peak2_start, peak2_end = datetime.strptime("16:00", "%H:%M").time(), datetime.strptime("20:00", "%H:%M").time()

        # Step 2: Base Peak Hour Surge
        if (peak1_start <= target_time <= peak1_end) or (peak2_start <= target_time <= peak2_end):
            multiplier = max(multiplier, 1.3)
            
        # Step 2.5: Environmental Surge (Weather & Traffic)
        try:
            env_surge = 1.0
            
            # Weather
            if enable_weather and lat and lng:
                w_surge = WeatherService.get_weather_surge(lat, lng)
                w_surge = min(w_surge, max_weather) # Cap at admin limit
                env_surge = max(env_surge, w_surge)
                
            # Traffic
            if enable_traffic and duration_seconds and duration_in_traffic:
                if duration_in_traffic > duration_seconds:
                    delay_ratio = duration_in_traffic / float(duration_seconds)
                    if delay_ratio > 1.2: # More than 20% delay
                        t_surge = 1.0 + ((delay_ratio - 1.2) / 2.0) # E.g., 1.5 ratio -> 1.0 + 0.15 = 1.15
                        t_surge = min(t_surge, max_traffic) # Cap at admin limit
                        env_surge = max(env_surge, t_surge)
                        
            multiplier = max(multiplier, env_surge)
        except Exception as e:
            logger.error(f"Error calculating environmental surge: {e}")
        
        # Step 3: Dynamic Spatial Demand Surge
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
    def compute_final_fare(distance_km, vehicle_category_slug, waiting_minutes=0, payment_method='cash', is_cancelled=False, surge_override=None, num_stops=0, lat=None, lng=None, is_sharing_enabled=False):
        """
        Final Fare Calculation Sequence (8 Stages - Screenshot 7)
        """
        ledger = {
            'base_fare': 0.0,
            'distance_fare': 0.0,
            'stops_fee': 0.0,
            'waiting_fee': 0.0,
            'cancellation_fee': 0.0,
            'surge_multiplier': 1.0,
            'total_fare': 0.0,
            'driver_payout': 0.0
        }

        categories = FareCalculator._get_active_categories()
        category = next((c for c in categories if c.slug == vehicle_category_slug), None)
        if not category:
            try:
                category = VehicleCategory.objects.get(slug=vehicle_category_slug)
            except VehicleCategory.DoesNotExist:
                logger.error(f"Category {vehicle_category_slug} not found.")
                return ledger

        rules = FareCalculator._get_active_pricing_rules()
        rule = None
        if lat is not None and lng is not None:
            min_dist = float('inf')
            for r in rules:
                if r.city and r.city.is_active and r.city.latitude is not None and r.city.longitude is not None:
                    dist = GeospatialUtils.calculate_haversine_distance(lat, lng, r.city.latitude, r.city.longitude) / 1000.0
                    if dist < 100.0 and dist < min_dist:
                        min_dist = dist
                        rule = r
        
        if not rule:
            rule = next((r for r in rules if r.city is None), None)
            if not rule and rules:
                rule = rules[0]

        # Stage 1: Add Base Fare
        if rule and rule.base_fare > 0:
            ledger['base_fare'] = rule.base_fare * category.multiplier
        else:
            ledger['base_fare'] = category.base_fare

        # Stage 2 & 3: Add Distance Charges + Category Multiplier
        if rule and rule.per_km_rate > 0:
            # City-specific flat per-km rate override
            tiered_dist_charge = distance_km * rule.per_km_rate * category.multiplier
        else:
            # Default Distance Tiers fallback
            tiers = FareCalculator._get_active_distance_tiers()
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
        ledger['surge_multiplier'] = surge_override if surge_override is not None else FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        ledger['distance_fare'] = tiered_dist_charge * ledger['surge_multiplier']

        # Stage 5: Add Stops Fee (GHS 2 per extra stop)
        if num_stops > 0:
            ledger['stops_fee'] = num_stops * 2.0

        # Stage 6: Add Waiting Fee
        ledger['waiting_fee'] = FareCalculator.calculate_waiting_fee(waiting_minutes)

        # Stage 7: Apply Cancellation Logic
        if is_cancelled:
            # GHS 8 fee only for card/momo
            if payment_method.lower() in ['card', 'momo', 'wallet']:
                ledger['cancellation_fee'] = 8.0
            else:
                ledger['cancellation_fee'] = 0.0

        # Apply Carpooling / Shared Ride Discount (20% off base and distance charges)
        if is_sharing_enabled:
            ledger['base_fare'] = round(ledger['base_fare'] * 0.80, 2)
            ledger['distance_fare'] = round(ledger['distance_fare'] * 0.80, 2)

        # Stage 8: Format Final Amount
        total = ledger['base_fare'] + ledger['distance_fare'] + ledger['stops_fee'] + ledger['waiting_fee'] + ledger['cancellation_fee']
        ledger['total_fare'] = round(total, 2)

        # Stage 9: Payout Assignment (100% to driver)
        ledger['driver_payout'] = ledger['total_fare']

        return ledger

    @staticmethod
    def calculate_fare_estimates(distance_km, duration_seconds, is_sharing_enabled=False):
        """
        Provides estimates for all active categories (Simplified 8-stage).
        """
        categories = VehicleCategory.objects.filter(is_active=True)
        estimates = {}
        
        for category in categories:
            ledger = FareCalculator.compute_final_fare(distance_km, category.slug, is_sharing_enabled=is_sharing_enabled)
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

