from core_settings.models import DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
from rides.utils import FareCalculator
from flexy_backend.engine_client import engine_client
import logging

logger = logging.getLogger(__name__)

class CourierFareCalculator:
    @staticmethod
    def compute_final_fare(distance_km, vehicle_type_id, category_id=None, weight_tier_id=None, lat=None, lng=None, promo_code=None, driver_billing_model="subscription", is_trial=False):
        """
        Calculates delivery fare based on distance, weight tier markup, category markup, and vehicle type,
        via flexy-engine with automatic fallback.
        """
        surge = FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        promo_discount = 0.0

        # 1. Attempt Go engine calculation
        try:
            engine_ledger = engine_client.compute_courier_fare(
                distance_km=distance_km,
                vehicle_type_id=vehicle_type_id,
                category_id=category_id,
                weight_tier_id=weight_tier_id,
                surge_multiplier=surge,
                promo_discount=promo_discount,
                driver_billing_model=driver_billing_model,
                is_trial=is_trial
            )
            if engine_ledger and "total_fare" in engine_ledger:
                return engine_ledger
        except Exception as e:
            logger.warning(f"Engine compute_courier_fare fallback: {e}")

        # 2. Python Reference Fallback
        ledger = {
            'base_fare': 0.0,
            'distance_fare': 0.0,
            'surge_multiplier': surge,
            'weight_markup': 0.0,
            'category_markup': 0.0,
            'total_fare': 0.0,
            'discount_amount': promo_discount,
            'billing_model': driver_billing_model,
            'is_in_trial': is_trial,
            'commission_rate': 10.0,
            'commission_amount': 0.0,
            'driver_payout': 0.0,
        }

        try:
            vehicle = DeliveryVehicleType.objects.get(id=vehicle_type_id)
            ledger['base_fare'] = vehicle.base_fare
            ledger['distance_fare'] = round(distance_km * vehicle.per_km_rate * ledger['surge_multiplier'], 2)
        except DeliveryVehicleType.DoesNotExist:
            logger.error(f"DeliveryVehicleType {vehicle_type_id} not found.")
            return ledger

        sub_total = ledger['base_fare'] + ledger['distance_fare']

        if weight_tier_id:
            try:
                weight_tier = DeliveryWeightTier.objects.get(id=weight_tier_id)
                if weight_tier.markup_percentage > 0:
                    ledger['weight_markup'] = round(sub_total * (weight_tier.markup_percentage / 100.0), 2)
            except DeliveryWeightTier.DoesNotExist:
                pass

        if category_id:
            try:
                category = DeliveryCategory.objects.get(id=category_id)
                if category.markup_percentage > 0:
                    ledger['category_markup'] = round(sub_total * (category.markup_percentage / 100.0), 2)
            except DeliveryCategory.DoesNotExist:
                pass

        total_before_discount = sub_total + ledger['weight_markup'] + ledger['category_markup']
        total = max(0.0, total_before_discount - ledger['discount_amount'])
        ledger['total_fare'] = round(total, 2)

        if driver_billing_model == "subscription" or is_trial:
            ledger['commission_amount'] = 0.0
            ledger['driver_payout'] = ledger['total_fare']
        else:
            comm = round(ledger['total_fare'] * 0.10, 2)
            ledger['commission_amount'] = comm
            ledger['driver_payout'] = round(ledger['total_fare'] - comm, 2)

        return ledger
