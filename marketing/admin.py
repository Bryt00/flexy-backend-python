from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import PromoCode, Campaign

@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'times_used', 'usage_limit')
    list_filter = ('is_active',)

@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    list_display = ('title', 'target_audience', 'status', 'scheduled_at', 'created_at')
    list_filter = ('status', 'target_audience')
    search_fields = ('title', 'description')
