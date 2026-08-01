from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminTextInputWidget
from .models import Vehicle
class VehicleAdmin(ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': UnfoldAdminTextInputWidget},
    }
    list_per_page = 20
    list_display = ('license_plate', 'make', 'model', 'type', 'status', 'is_active', 'is_verified', 'driver')
    list_filter = ('type', 'status', 'is_active', 'is_verified', 'created_at', 'updated_at')
    search_fields = ('license_plate', 'make', 'model', 'driver__user__email', 'driver__full_name')
    list_editable = ('is_active', 'is_verified', 'status')
    list_per_page = 25
    ordering = ('-is_active', '-is_verified', 'license_plate')

    fieldsets = (
        ('Vehicle Identity', {
            'fields': ('driver', 'make', 'model', 'year', 'license_plate', 'color', 'type'),
        }),
        ('Operational Status', {
            'fields': ('status', 'is_active', 'is_verified'),
        }),
        ('Documents', {
            'fields': ('license_url', 'insurance_url', 'roadworthy_url', 'video_url', 'insurance_expiry', 'roadworthy_expiry'),
            'classes': ('collapse',),
        }),
    )
