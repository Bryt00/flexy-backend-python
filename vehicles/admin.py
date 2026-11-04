from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminTextInputWidget
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('license_plate', 'make', 'model', 'type', 'status', 'is_active', 'is_verified', 'driver')
    list_filter = ('type', 'status', 'is_active', 'is_verified', 'created_at', 'updated_at')
    search_fields = ('license_plate', 'make', 'model', 'driver__user__email', 'driver__full_name')
    list_editable = ('is_active', 'is_verified', 'status')
    ordering = ('-is_active', '-is_verified', 'license_plate')

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, models.TextField):
            kwargs['widget'] = UnfoldAdminTextInputWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

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
