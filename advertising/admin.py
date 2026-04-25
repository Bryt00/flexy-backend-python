from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import AdSlotCapacity, AdBooking, AdExtension
# We will import the email tasks here later for approval/rejection

@admin.register(AdSlotCapacity)
class AdSlotCapacityAdmin(SingletonModelAdmin):
    pass

class AdExtensionInline(admin.TabularInline):
    model = AdExtension
    extra = 0

@admin.register(AdBooking)
class AdBookingAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'week_start_date', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'week_start_date')
    search_fields = ('business_name', 'contact_email', 'contact_phone')
    inlines = [AdExtensionInline]
    
    actions = ['approve_bookings', 'reject_bookings']
    
    def approve_bookings(self, request, queryset):
        # We will dispatch the approve email task here
        queryset.update(status='APPROVED')
        self.message_user(request, f"Approved {queryset.count()} bookings.")
        
        # trigger celery task to send email
        # from .tasks import send_ad_approved_email
        # for booking in queryset:
        #    send_ad_approved_email.delay(booking.id)
    approve_bookings.short_description = "Approve selected bookings"

    def reject_bookings(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, f"Rejected {queryset.count()} bookings.")
    reject_bookings.short_description = "Reject selected bookings"

@admin.register(AdExtension)
class AdExtensionAdmin(admin.ModelAdmin):
    list_display = ('get_business_name', 'extended_week_start', 'status', 'payment_status')
    list_filter = ('status', 'payment_status', 'extended_week_start')

    def get_business_name(self, obj):
        return obj.original_booking.business_name
    get_business_name.short_description = 'Business Name'
