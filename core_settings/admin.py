from django.contrib import admin
from django.db import models
from django.forms import TextInput
from unfold.admin import ModelAdmin
from .models import SiteSetting, LegalDocument, PricingRule, VehicleCategory, DistanceTier, DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType

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
    list_display = ('display_name', 'slug', 'base_fare', 'multiplier', 'image', 'is_active')
    list_filter = ('created_at',)
    list_editable = ('base_fare', 'multiplier', 'is_active')
    search_fields = ('display_name', 'slug')

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


