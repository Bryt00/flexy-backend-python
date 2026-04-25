from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_display = ('name', 'category', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    ordering = ('category', 'price')

@admin.register(DriverSubscription)
class DriverSubscriptionAdmin(ModelAdmin):
    list_display = ('profile', 'plan', 'status', 'start_date', 'expiry_date', 'is_currently_active')
    list_filter = ('status', 'plan__category')
    search_fields = ('profile__user__email', 'profile__first_name', 'profile__last_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(ModelAdmin):
    list_display = ('paystack_reference', 'subscription', 'amount', 'status', 'payment_date')
    list_filter = ('status',)
    search_fields = ('paystack_reference', 'subscription__profile__user__email')
    readonly_fields = ('created_at',)
