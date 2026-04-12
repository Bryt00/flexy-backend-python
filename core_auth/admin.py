from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import User, DeletionRequest

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('email',)

@admin.register(DeletionRequest)
class DeletionRequestAdmin(ModelAdmin):
    list_display = ('user', 'status', 'requested_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('user__email',)
    list_editable = ('status',)
