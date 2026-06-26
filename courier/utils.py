from core_settings.models import DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
from rides.utils import FareCalculator
import logging

logger = logging.getLogger(__name__)

class CourierFareCalculator:
    @staticmethod
    def compute_final_fare(distance_km, vehicle_type_id, category_id=None, weight_tier_id=None, lat=None, lng=None, promo_code=None):
        """
        Calculates delivery fare based strictly on distance, weight tier markup, category markup, and vehicle type.
        """
        ledger = {
            'base_fare': 0.0,
            'distance_fare': 0.0,
            'surge_multiplier': 1.0,
            'weight_markup': 0.0,
            'category_markup': 0.0,
            'total_fare': 0.0,
            'discount_amount': 0.0,
        }

        # 1. Get Vehicle Type (Determines base and per_km rate)
        try:
            vehicle = DeliveryVehicleType.objects.get(id=vehicle_type_id)
            ledger['base_fare'] = vehicle.base_fare
            ledger['distance_fare'] = distance_km * vehicle.per_km_rate
        except DeliveryVehicleType.DoesNotExist:
            logger.error(f"DeliveryVehicleType {vehicle_type_id} not found.")
            return ledger

        # 2. Get Surge Multiplier (Re-use ride surge logic)
        ledger['surge_multiplier'] = FareCalculator.get_surge_multiplier(lat=lat, lng=lng)
        
        # Apply surge to distance fare
        ledger['distance_fare'] = ledger['distance_fare'] * ledger['surge_multiplier']

        # 3. Calculate preliminary total
        sub_total = ledger['base_fare'] + ledger['distance_fare']

        # 4. Apply Weight Tier Markup
        if weight_tier_id:
            try:
                weight_tier = DeliveryWeightTier.objects.get(id=weight_tier_id)
                if weight_tier.markup_percentage > 0:
                    ledger['weight_markup'] = sub_total * (weight_tier.markup_percentage / 100.0)
            except DeliveryWeightTier.DoesNotExist:
                pass

        # 5. Apply Category Markup
        if category_id:
            try:
                category = DeliveryCategory.objects.get(id=category_id)
                if category.markup_percentage > 0:
                    ledger['category_markup'] = sub_total * (category.markup_percentage / 100.0)
            except DeliveryCategory.DoesNotExist:
                pass

        total_before_discount = sub_total + ledger['weight_markup'] + ledger['category_markup']

        # 6. Apply Promo Code (Optional, future proofing)
        if promo_code:
            # Add your promo logic here
            pass
            
        ledger['total_fare'] = round(total_before_discount - ledger['discount_amount'], 2)

        return ledger
