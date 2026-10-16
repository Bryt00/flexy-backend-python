import logging
from rides.utils import FareCalculator
from flexy_backend.engine_client import engine_client

logger = logging.getLogger(__name__)

class PricingService:
    @staticmethod
    def get_surge_multiplier(lat=None, lng=None, radius=5.0, duration_seconds=None, duration_in_traffic=None):
        """
        Calculates compounded surge multiplier via flexy-engine, with automatic fallback to FareCalculator.
        """
        try:
            val = engine_client.get_surge_multiplier(
                lat=lat, lng=lng, radius=radius,
                duration_seconds=duration_seconds,
                duration_in_traffic=duration_in_traffic
            )
            if val is not None:
                return val
        except Exception as e:
            logger.warning(f"Engine get_surge_multiplier fallback: {e}")

        return FareCalculator.get_surge_multiplier(
            lat=lat, lng=lng, radius=radius,
            duration_seconds=duration_seconds,
            duration_in_traffic=duration_in_traffic
        )

    @staticmethod
    def calculate_fare_estimates(dist_km, duration_sec, lat=None, lng=None, d_lat=None, d_lng=None, num_stops=0, duration_in_traffic_sec=None, is_sharing=False):
        """
        Calculates fare estimates across active vehicle categories using flexy-engine,
        handling PostGIS geofence checks and falling back to Python if engine is unavailable.
        """
        from core_settings.models import VehicleCategory
        from django.contrib.gis.geos import Point
        
        pickup_point = Point(float(lng), float(lat), srid=4326) if lat and lng else None
        dropoff_point = Point(float(d_lng), float(d_lat), srid=4326) if d_lat and d_lng else None
        categories = list(VehicleCategory.objects.filter(is_active=True))

        # Check geofence restrictions
        disallowed_slugs = set()
        for category in categories:
            if not getattr(category, 'is_passenger_allowed', True):
                if not pickup_point or not dropoff_point:
                    disallowed_slugs.add(category.slug)
                    continue
                allowed_areas = category.allowed_service_areas.all()
                if not allowed_areas:
                    disallowed_slugs.add(category.slug)
                    continue
                p_ok = any(area.polygon.contains(pickup_point) for area in allowed_areas)
                d_ok = any(area.polygon.contains(dropoff_point) for area in allowed_areas)
                if not (p_ok and d_ok):
                    disallowed_slugs.add(category.slug)

        # 1. Attempt Go engine call
        try:
            res = engine_client.calculate_fare_estimates(
                dist_km=dist_km,
                duration_sec=duration_sec,
                lat=lat, lng=lng,
                num_stops=num_stops,
                is_sharing=is_sharing,
                duration_in_traffic=duration_in_traffic_sec
            )
            if res and "estimates" in res:
                return {k: v for k, v in res["estimates"].items() if k not in disallowed_slugs}
        except Exception as e:
            logger.warning(f"Engine calculate_fare_estimates fallback: {e}")

        # 2. Python Reference Fallback
        surge = FareCalculator.get_surge_multiplier(
            lat=lat, lng=lng,
            duration_seconds=duration_sec,
            duration_in_traffic=duration_in_traffic_sec
        )
        estimates = {}
        for category in categories:
            if category.slug in disallowed_slugs:
                continue
            ledger = FareCalculator.compute_final_fare(
                dist_km, 
                category.slug, 
                surge_override=surge,
                num_stops=num_stops,
                lat=lat,
                lng=lng,
                is_sharing_enabled=is_sharing
            )
            estimates[category.slug] = ledger['total_fare']
            
        return estimates

    @staticmethod
    def compute_final_fare(distance_km, vehicle_category_slug, lat=None, lng=None, waiting_minutes=0, payment_method='cash', num_stops=0, is_sharing=False, is_cancelled=False, driver_billing_model="subscription", is_trial=False):
        """
        Computes the final 9-stage pricing & commission ledger for a completed ride.
        """
        # 1. Attempt Go engine call
        try:
            res = engine_client.compute_final_fare(
                distance_km=distance_km,
                category_slug=vehicle_category_slug,
                lat=lat, lng=lng,
                waiting_minutes=waiting_minutes,
                payment_method=payment_method,
                num_stops=num_stops,
                is_sharing=is_sharing,
                is_cancelled=is_cancelled,
                driver_billing_model=driver_billing_model,
                is_trial=is_trial
            )
            if res and "total_fare" in res:
                return res
        except Exception as e:
            logger.warning(f"Engine compute_final_fare fallback: {e}")

        # 2. Python Reference Fallback
        surge = FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        ledger = FareCalculator.compute_final_fare(
            distance_km=distance_km,
            vehicle_category_slug=vehicle_category_slug,
            waiting_minutes=waiting_minutes,
            payment_method=payment_method,
            surge_override=surge,
            num_stops=num_stops,
            lat=lat,
            lng=lng,
            is_sharing_enabled=is_sharing,
            is_cancelled=is_cancelled
        )
        # Augment ledger with billing model
        ledger['billing_model'] = driver_billing_model
        ledger['is_in_trial'] = is_trial
        ledger['commission_rate'] = 10.0
        ledger['commission_flat'] = 0.0
        if driver_billing_model == "subscription" or is_trial:
            ledger['commission_amount'] = 0.0
            ledger['driver_payout'] = ledger['total_fare']
        else:
            comm = round(ledger['total_fare'] * 0.10, 2)
            ledger['commission_amount'] = comm
            ledger['driver_payout'] = round(ledger['total_fare'] - comm, 2)
            
        return ledger
