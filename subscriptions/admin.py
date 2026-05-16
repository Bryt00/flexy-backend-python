from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'category', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    ordering = ('category', 'price')

@admin.register(DriverSubscription)
class DriverSubscriptionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('profile', 'plan', 'status', 'trial_end_date', 'expiry_date', 'is_in_trial', 'is_currently_active')
    list_filter = ('status', 'is_trial_used', 'plan__category')
    search_fields = ('profile__user__email', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')
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
    list_display = ('paystack_reference', 'subscription', 'amount', 'status', 'payment_date')
    list_filter = ('status',)
    search_fields = ('paystack_reference', 'subscription__profile__user__email')
    readonly_fields = ('created_at',)
