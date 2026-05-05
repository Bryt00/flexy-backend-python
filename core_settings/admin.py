from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteSetting, LegalDocument, PricingRule, VehicleCategory, DistanceTier

@admin.register(SiteSetting)
class SiteSettingAdmin(ModelAdmin):
    list_display = ('key', 'value', 'updated_at')
    search_fields = ('key', 'value')

@admin.register(LegalDocument)
class LegalDocumentAdmin(ModelAdmin):
    list_display = ('title', 'version', 'is_active', 'created_at')
    list_filter = ('is_active',)

@admin.register(PricingRule)
class PricingRuleAdmin(ModelAdmin):
    list_display = ('city', 'base_fare', 'surge_multiplier', 'is_active')
    list_editable = ('surge_multiplier', 'is_active')

@admin.register(VehicleCategory)
class VehicleCategoryAdmin(ModelAdmin):
    list_display = ('display_name', 'slug', 'base_fare', 'multiplier', 'image', 'is_active')
    list_editable = ('base_fare', 'multiplier', 'is_active')
    search_fields = ('display_name', 'slug')

@admin.register(DistanceTier)
class DistanceTierAdmin(ModelAdmin):
    list_display = ('name', 'min_km', 'max_km', 'rate_per_km', 'is_active')
    list_editable = ('rate_per_km', 'is_active')

