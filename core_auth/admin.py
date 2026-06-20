from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import User, DeletionRequest

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('email', 'full_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at', 'updated_at')
    search_fields = ('email',)
    
    def full_name(self, obj):
        try:
            return obj.profile.full_name or "—"
        except Exception:
            return "—"
    full_name.short_description = 'Full Name'
    
    # Secure the form by excluding sensitive fields
    exclude = ('password',)
    
    fieldsets = (
        (None, {"fields": ("email", "role", "is_active")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ('created_at', 'last_login')

@admin.register(DeletionRequest)
class DeletionRequestAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at', 'processed_at')
    search_fields = ('user__email',)
    list_editable = ('status',)
