from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    list_display = ('license_plate', 'make', 'model', 'status')
