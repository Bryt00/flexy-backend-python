from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Ride, Incident, RideStop, RideReceipt


class RideStopInline(admin.TabularInline):
    model = RideStop
    extra = 0
    fields = ('stop_order', 'address', 'status', 'arrived_at', 'completed_at')
    readonly_fields = ('arrived_at', 'completed_at')


@admin.register(Ride)
class RideAdmin(ModelAdmin):
    inlines = [RideStopInline]
    list_display = ('short_id', 'rider', 'driver', 'status_badge', 'type', 'fare_display', 'has_incidents', 'created_at')
    list_filter = ('status', 'type', 'is_scheduled', 'preferred_vehicle_type')
    search_fields = ('id', 'rider__email', 'driver__user__email', 'pickup_address', 'dropoff_address')
    readonly_fields = ('id', 'created_at', 'updated_at', 'dispatch_metadata', 'has_incidents')
    list_per_page = 30
    ordering = ('-created_at',)

    fieldsets = (
        ('Ride Identity', {
            'fields': ('id', 'rider', 'driver', 'type', 'status', 'preferred_vehicle_type'),
        }),
        ('Route', {
            'fields': ('pickup_address', 'pickup_lat', 'pickup_lng', 'dropoff_address', 'dropoff_lat', 'dropoff_lng', 'distance'),
        }),
        ('Financials', {
            'fields': (
                'fare', 'payment_method', 
                'base_fare_ledger', 'distance_fare_ledger', 'stops_fee_ledger', 
                'waiting_fare_ledger', 'cancellation_fee_ledger', 
                'surge_multiplier_applied', 'total_calculated_fare', 'discount_amount',
                'driver_payout_amount'
            ),
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'scheduled_for'),
        }),
        ('Internal', {
            'fields': ('dispatch_metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def short_id(self, obj):
        return str(obj.id)[:8] + '…'
    short_id.short_description = 'ID'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'requested': '#3b82f6',
            'accepted': '#8b5cf6',
            'arrived': '#06b6d4',
            'in_progress': '#22c55e',
            'completed': '#10b981',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#94a3b8')
        return format_html(
            '<span style="background:{}22; color:{}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid {}44;">{}</span>',
            color, color, color, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def fare_display(self, obj):
        if obj.fare:
            formatted_fare = f"{float(obj.fare):.2f}"
            return format_html('<strong style="color:#22c55e;">GHS {}</strong>', formatted_fare)
        return '—'
    fare_display.short_description = 'Fare'
    
    def has_incidents(self, obj):
        count = obj.incidents.count()
        if count > 0:
            return format_html('<span style="color:#ef4444; font-weight:bold;">⚠️ {} INCIDENTS</span>', count)
        return format_html('<span style="color:#94a3b8;">{}</span>', 'None')
    has_incidents.short_description = 'Safety'


@admin.register(Incident)
class IncidentAdmin(ModelAdmin):
    list_display = ('type', 'ride', 'reporter', 'status', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('ride__id', 'reporter__email', 'description')
    list_editable = ('status',)
@admin.register(RideReceipt)
class RideReceiptAdmin(ModelAdmin):
    list_display = ('receipt_no', 'ride', 'total_fare', 'generated_at')
    search_fields = ('receipt_no', 'ride__id')
    readonly_fields = ('generated_at',)
    
    fieldsets = (
        ('General', {
            'fields': ('receipt_no', 'ride', 'generated_at'),
        }),
        ('Ledger Breakdown', {
            'fields': ('base_fare', 'distance_fare', 'stops_fee', 'waiting_fee', 'cancellation_fee', 'total_fare'),
        }),
    )
