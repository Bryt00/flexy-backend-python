from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from core_settings.models import VehicleCategory, SiteSetting

@receiver(post_save, sender=VehicleCategory)
@receiver(post_delete, sender=VehicleCategory)
def invalidate_vehicle_category_cache(sender, instance, **kwargs):
    """
    Invalidates the cached active vehicle categories list.
    """
    cache.delete("active_vehicle_categories_list")

@receiver(post_save, sender=SiteSetting)
@receiver(post_delete, sender=SiteSetting)
def invalidate_site_setting_cache(sender, instance, **kwargs):
    """
    Invalidates the cached site setting value.
    """
    cache_key = f"site_setting_{instance.key}"
    cache.delete(cache_key)
