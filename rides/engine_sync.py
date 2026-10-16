import json
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from flexy_backend.redis_client import redis_geo

logger = logging.getLogger(__name__)

REDIS_CONFIG_KEY = "engine:config:pricing"

def serialize_pricing_config():
    """
    Serializes current active categories, distance tiers, pricing rules,
    and delivery configurations into a JSON-serializable dictionary.
    """
    from core_settings.models import (
        VehicleCategory, DistanceTier, PricingRule,
        DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
    )

    categories = []
    for c in VehicleCategory.objects.filter(is_active=True):
        categories.append({
            "slug": c.slug,
            "name": getattr(c, 'display_name', c.slug),
            "base_fare": float(c.base_fare),
            "multiplier": float(c.multiplier),
            "is_active": c.is_active,
            "is_passenger_allowed": getattr(c, 'is_passenger_allowed', True),
        })

    distance_tiers = []
    for dt in DistanceTier.objects.filter(is_active=True).order_by('min_km'):
        distance_tiers.append({
            "min_km": float(dt.min_km),
            "max_km": float(dt.max_km),
            "rate_per_km": float(dt.rate_per_km),
            "is_active": dt.is_active,
        })

    pricing_rules = []
    for r in PricingRule.objects.filter(is_active=True).select_related('city'):
        pricing_rules.append({
            "id": str(r.id),
            "city_id": str(r.city.id) if r.city else None,
            "city_name": r.city.name if r.city else None,
            "city_lat": float(r.city.latitude) if r.city and r.city.latitude is not None else None,
            "city_lng": float(r.city.longitude) if r.city and r.city.longitude is not None else None,
            "city_is_active": r.city.is_active if r.city else False,
            "base_fare": float(r.base_fare),
            "per_km_rate": float(r.per_km_rate),
            "surge_multiplier": float(r.surge_multiplier),
            "enable_weather_surge": r.enable_weather_surge,
            "max_weather_surge": float(r.max_weather_surge),
            "enable_traffic_surge": r.enable_traffic_surge,
            "max_traffic_surge": float(r.max_traffic_surge),
            "is_active": r.is_active,
        })

    delivery_categories = []
    for dc in DeliveryCategory.objects.filter(is_active=True):
        delivery_categories.append({
            "id": str(dc.id),
            "name": dc.name,
            "markup_percentage": float(dc.markup_percentage),
            "is_active": dc.is_active,
        })

    delivery_weight_tiers = []
    for dwt in DeliveryWeightTier.objects.filter(is_active=True):
        delivery_weight_tiers.append({
            "id": str(dwt.id),
            "name": dwt.name,
            "min_weight_kg": float(getattr(dwt, 'min_weight', 0.0)),
            "max_weight_kg": float(getattr(dwt, 'max_weight', 0.0)),
            "markup_percentage": float(dwt.markup_percentage),
            "is_active": dwt.is_active,
        })

    delivery_vehicle_types = []
    for dvt in DeliveryVehicleType.objects.filter(is_active=True):
        delivery_vehicle_types.append({
            "id": str(dvt.id),
            "name": dvt.name,
            "base_fare": float(dvt.base_fare),
            "per_km_rate": float(dvt.per_km_rate),
            "is_active": dvt.is_active,
        })

    return {
        "categories": categories,
        "distance_tiers": distance_tiers,
        "pricing_rules": pricing_rules,
        "delivery_categories": delivery_categories,
        "delivery_weight_tiers": delivery_weight_tiers,
        "delivery_vehicle_types": delivery_vehicle_types,
        "commission_rules": [],
        "default_commission_pct": 10.0,
    }

def sync_pricing_config_to_redis():
    """
    Writes the pricing configuration snapshot into Redis for flexy-engine.
    """
    try:
        data = serialize_pricing_config()
        payload = json.dumps(data)
        redis_geo.r.set(REDIS_CONFIG_KEY, payload)
        logger.info("Synced pricing configuration snapshot to Redis key '%s'", REDIS_CONFIG_KEY)
        return True
    except Exception as e:
        logger.error("Failed to sync pricing config to Redis: %s", e)
        return False


def register_engine_signals():
    """
    Connects post_save and post_delete handlers on configuration models.
    """
    from core_settings.models import (
        VehicleCategory, DistanceTier, PricingRule,
        DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
    )

    models_to_track = [
        VehicleCategory, DistanceTier, PricingRule,
        DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
    ]

    def _sync_handler(sender, **kwargs):
        sync_pricing_config_to_redis()

    for m in models_to_track:
        post_save.connect(_sync_handler, sender=m, weak=False)
        post_delete.connect(_sync_handler, sender=m, weak=False)
