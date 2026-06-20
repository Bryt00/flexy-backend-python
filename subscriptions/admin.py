from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'category', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('category', 'price')

@admin.register(DriverSubscription)
class DriverSubscriptionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('driver_display', 'plan', 'status', 'trial_end_date', 'expiry_date', 'is_in_trial', 'is_currently_active')
    list_filter = ('status', 'is_trial_used', 'plan__category', 'created_at', 'updated_at', 'start_date', 'expiry_date')
    search_fields = ('profile__user__email', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')

    def driver_display(self, obj):
        try:
            full_name = obj.profile.full_name
            if full_name:
                return f"{full_name} ({obj.profile.user.email})"
            return obj.profile.user.email
        except Exception:
            return "—"
    driver_display.short_description = 'Driver'

    fieldsets = (
        (None, {
            'fields': ('profile', 'plan', 'status')
        }),
        ('Trial Information', {
            'fields': ('is_trial_used', 'trial_end_date')
        }),
        ('Dates', {
            'fields': ('start_date', 'expiry_date', 'auto_renew')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('paystack_reference', 'driver_display', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'created_at', 'payment_date')
    search_fields = ('paystack_reference', 'subscription__profile__user__email', 'subscription__profile__full_name')
    readonly_fields = ('created_at',)

    def driver_display(self, obj):
        try:
            profile = obj.subscription.profile
            full_name = profile.full_name
            if full_name:
                return f"{full_name} ({profile.user.email})"
            return profile.user.email
        except Exception:
            return "—"
    driver_display.short_description = 'Driver'
