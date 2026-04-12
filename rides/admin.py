from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Ride, Incident

@admin.register(Ride)
class RideAdmin(ModelAdmin):
    list_display = ('id', 'rider', 'driver', 'status', 'service_type', 'fare', 'created_at')
    list_filter = ('status', 'service_type')
    search_fields = ('id', 'rider__email', 'driver__user__email')

@admin.register(Incident)
class IncidentAdmin(ModelAdmin):
    list_display = ('type', 'ride', 'reporter', 'status', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('ride__id', 'reporter__email', 'description')
    list_editable = ('status',)
