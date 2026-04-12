from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AuditLog, FraudFlag

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ('user', 'action', 'entity_type', 'created_at')
    list_filter = ('action', 'entity_type')
    search_fields = ('user__email', 'action', 'entity_id')

@admin.register(FraudFlag)
class FraudFlagAdmin(ModelAdmin):
    list_display = ('type', 'user', 'severity', 'status', 'created_at')
    list_filter = ('type', 'severity', 'status')
    search_fields = ('user__email', 'details')
    list_editable = ('status', 'severity')
