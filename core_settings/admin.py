from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteSetting, LegalDocument, PricingRule

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
