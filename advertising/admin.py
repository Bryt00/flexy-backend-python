from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from solo.admin import SingletonModelAdmin
from .models import AdSlotCapacity, AdBooking, AdExtension, AdAnalytics
from integrations.email_service import EmailService
# We will import the email tasks here later for approval/rejection

@admin.register(AdSlotCapacity)
class AdSlotCapacityAdmin(SingletonModelAdmin):
    pass

class AdExtensionInline(TabularInline):
    model = AdExtension
    extra = 0

@admin.register(AdBooking)
class AdBookingAdmin(ModelAdmin):
    list_display = ('business_name', 'target_url', 'week_start_date', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'week_start_date')
    search_fields = ('business_name', 'contact_email', 'contact_phone', 'target_url')
    inlines = [AdExtensionInline]

@admin.register(AdAnalytics)
class AdAnalyticsAdmin(ModelAdmin):
    list_display = ('ad_booking', 'total_impressions', 'total_clicks', 'last_updated')
    readonly_fields = ('ad_booking', 'impressions_a', 'clicks_a', 'impressions_b', 'clicks_b', 'last_updated')

    def total_impressions(self, obj):
        return obj.impressions_a + obj.impressions_b
    
    def total_clicks(self, obj):
        return obj.clicks_a + obj.clicks_b
    
    actions = ['approve_bookings', 'reject_bookings', 'generate_ai_content']
    
    def generate_ai_content(self, request, queryset):
        # This is where the admin can trigger AI generation for the selected ads
        # In a real scenario, this would call Gemini/GPT API
        for ad in queryset:
            ad.headline = f"✨ [AI] {ad.headline}"
            ad.body_text = f"Optimized by AI: {ad.body_text}"
            ad.save()
        self.message_user(request, f"Generated AI content for {queryset.count()} ads.")
    generate_ai_content.short_description = "✨ Generate AI Content (Admin Only)"

    def approve_bookings(self, request, queryset):
        # We will dispatch the approve email task here
        queryset.update(status='APPROVED')
        self.message_user(request, f"Approved {queryset.count()} bookings.")
        
        # Notify businesses
        for booking in queryset:
            EmailService.send_ad_status_email(
                contact_email=booking.contact_email,
                business_name=booking.business_name,
                is_approved=True
            )
    approve_bookings.short_description = "Approve selected bookings"

    def reject_bookings(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, f"Rejected {queryset.count()} bookings.")

        # Notify businesses
        for booking in queryset:
            EmailService.send_ad_status_email(
                contact_email=booking.contact_email,
                business_name=booking.business_name,
                is_approved=False
            )
    reject_bookings.short_description = "Reject selected bookings"

@admin.register(AdExtension)
class AdExtensionAdmin(ModelAdmin):
    list_display = ('get_business_name', 'extended_week_start', 'status', 'payment_status')
    list_filter = ('status', 'payment_status', 'extended_week_start')

    def get_business_name(self, obj):
        return obj.original_booking.business_name
    get_business_name.short_description = 'Business Name'
