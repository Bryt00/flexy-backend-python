from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Profile, DriverVerification

@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ('user', 'full_name', 'phone_number', 'city', 'rating', 'online_status')
    search_fields = ('user__email', 'full_name', 'phone_number')
    list_filter = ('city', 'is_online')
    readonly_fields = ('online_status', 'last_location_update')

    def online_status(self, obj):
        if obj.is_online:
            return mark_safe(
                '<span style="color: #22c55e; font-weight: bold;">● Online</span>'
            )
        return mark_safe(
            '<span style="color: #94a3b8;">○ Offline</span>'
        )
    online_status.short_description = 'Online Status'
    online_status.allow_tags = True

@admin.register(DriverVerification)
class DriverVerificationAdmin(ModelAdmin):
    list_display = ('driver', 'assigned_category', 'status', 'is_verified', 'license_number', 'updated_at_display')
    list_filter = ('assigned_category', 'status', 'is_verified')
    search_fields = ('driver__user__email', 'driver__full_name', 'license_number')
    readonly_fields = ('license_preview', 'id_card_preview', 'insurance_preview', 'roadworthy_preview', 'video_link', 'verified_at')
    
    actions = ['approve_verification', 'reject_verification']

    def updated_at_display(self, obj):
        return obj.driver.updated_at
    updated_at_display.short_description = 'Last Updated'

    def license_preview(self, obj):
        if obj.license_url:
            return format_html('<a href="{0}" target="_blank" style="display:inline-block; padding:8px 16px; background:#2563eb; color:white; border-radius:6px; text-decoration:none; font-weight:500;">View License (PDF)</a>', obj.license_url)
        return "No document uploaded"
    
    def id_card_preview(self, obj):
        if obj.id_card_url:
            return format_html('<a href="{0}" target="_blank" style="display:inline-block; padding:8px 16px; background:#2563eb; color:white; border-radius:6px; text-decoration:none; font-weight:500;">View ID Card (PDF)</a>', obj.id_card_url)
        return "No document uploaded"

    def insurance_preview(self, obj):
        if obj.insurance_url:
            return format_html('<a href="{0}" target="_blank" style="display:inline-block; padding:8px 16px; background:#2563eb; color:white; border-radius:6px; text-decoration:none; font-weight:500;">View Insurance (PDF)</a>', obj.insurance_url)
        return "No document uploaded"

    def roadworthy_preview(self, obj):
        if obj.roadworthy_url:
            return format_html('<a href="{0}" target="_blank" style="display:inline-block; padding:8px 16px; background:#2563eb; color:white; border-radius:6px; text-decoration:none; font-weight:500;">View Roadworthy (PDF)</a>', obj.roadworthy_url)
        return "No document uploaded"

    def video_link(self, obj):
        if obj.vehicle_video_url:
            return format_html('<a href="{0}" target="_blank" style="display:inline-block; padding:8px 16px; background:#0f172a; color:white; border-radius:6px; text-decoration:none; font-weight:500;">Watch Vehicle Video</a>', obj.vehicle_video_url)
        return "No video uploaded"

    @admin.action(description='Approve selected driver verifications')
    def approve_verification(self, request, queryset):
        for verification in queryset:
            verification.approve()
        self.message_user(request, f"{queryset.count()} verification(s) have been approved and synchronized.")

    @admin.action(description='Reject selected driver verifications')
    def reject_verification(self, request, queryset):
        for verification in queryset:
            verification.reject()
        self.message_user(request, f"{queryset.count()} verification(s) have been rejected.")
