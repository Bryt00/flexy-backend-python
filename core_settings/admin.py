from django.contrib import admin
from django.db import models
from django.forms import TextInput
from unfold.admin import ModelAdmin
from django.contrib.gis import admin as gis_admin
from django.contrib.gis.db import models as gis_models
import unfold.templatetags.unfold

def _safe_flatten_context(context):
    flat = {}
    for d in context.dicts:
        if isinstance(d, dict):
            flat.update(d)
        elif hasattr(d, 'flatten') and callable(d.flatten):
            try:
                flat.update(d.flatten())
            except Exception:
                pass
        elif hasattr(d, 'keys'):
            for k in d.keys():
                flat[k] = d[k]
    return flat

unfold.templatetags.unfold._flatten_context = _safe_flatten_context

from .models import SiteSetting, LegalDocument, PricingRule, VehicleCategory, DistanceTier, DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType, ServiceArea

@admin.register(SiteSetting)
class SiteSettingAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('key', 'value', 'description', 'updated_at')
    list_editable = ('value',)
    list_filter = ('updated_at',)
    search_fields = ('key', 'value')
    
    formfield_overrides = {
        models.TextField: {'widget': TextInput(attrs={'size': '40', 'class': 'vTextField'})},
    }

    def get_readonly_fields(self, request, obj=None):
        if obj: # Editing an existing object
            return ('key', 'description')
        return ()

@admin.register(LegalDocument)
class LegalDocumentAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('title', 'version', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')

@admin.register(PricingRule)
class PricingRuleAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('city', 'base_fare', 'surge_multiplier', 'enable_weather_surge', 'enable_traffic_surge', 'is_active')
    list_filter = ('created_at',)
    list_editable = ('surge_multiplier', 'enable_weather_surge', 'enable_traffic_surge', 'is_active')
    fieldsets = (
        ('Standard Pricing', {
            'fields': ('city', 'base_fare', 'per_km_rate', 'per_minute_rate', 'surge_multiplier', 'is_active')
        }),
        ('Environmental Auto-Surge Controls', {
            'fields': ('enable_weather_surge', 'max_weather_surge', 'enable_traffic_surge', 'max_traffic_surge'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VehicleCategory)
class VehicleCategoryAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('display_name', 'slug', 'base_fare', 'multiplier', 'is_passenger_allowed', 'is_delivery_geofenced', 'is_active')
    list_filter = ('created_at', 'is_passenger_allowed', 'is_delivery_geofenced')
    list_editable = ('base_fare', 'multiplier', 'is_passenger_allowed', 'is_delivery_geofenced', 'is_active')
    search_fields = ('display_name', 'slug')
    filter_horizontal = ('allowed_service_areas',)

from django.contrib.gis.forms.widgets import OSMWidget


@admin.register(ServiceArea)
class ServiceAreaAdmin(ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    formfield_overrides = {
        gis_models.PolygonField: {
            'widget': OSMWidget(attrs={
                'map_width': 800,
                'map_height': 500,
                'default_lon': 0,
                'default_lat': 0,
                'default_zoom': 2,
                'style': 'width: 100% !important; min-width: 800px; height: 500px;'
            })
        },
    }



@admin.register(DistanceTier)
class DistanceTierAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'min_km', 'max_km', 'rate_per_km', 'is_active')
    list_editable = ('rate_per_km', 'is_active')

@admin.register(DeliveryCategory)
class DeliveryCategoryAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'markup_percentage', 'is_active', 'created_at')
    list_editable = ('markup_percentage', 'is_active')
    search_fields = ('name',)

@admin.register(DeliveryWeightTier)
class DeliveryWeightTierAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'min_weight', 'max_weight', 'markup_percentage', 'is_active')
    list_editable = ('min_weight', 'max_weight', 'markup_percentage', 'is_active')
    search_fields = ('name',)

@admin.register(DeliveryVehicleType)
class DeliveryVehicleTypeAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'base_fare', 'per_km_rate', 'is_active', 'created_at')
    list_editable = ('base_fare', 'per_km_rate', 'is_active')
    search_fields = ('name',)


