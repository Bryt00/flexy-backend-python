from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import PromoCode, Campaign

@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('code', 'discount_percentage', 'is_active', 'times_used', 'usage_limit')
    list_filter = ('is_active',)

@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('title', 'status', 'is_active', 'start_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'description')
