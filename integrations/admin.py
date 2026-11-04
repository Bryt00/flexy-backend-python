from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import APIKey

@admin.register(APIKey)
class APIKeyAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('name', 'user', 'environment', 'prefix', 'is_active', 'last_used_at', 'created_at')
    list_filter = ('environment', 'is_active', 'created_at')
    search_fields = ('name', 'user__email', 'prefix', 'webhook_url')
    readonly_fields = ('prefix', 'hashed_key', 'webhook_secret', 'created_at', 'last_used_at', 'last_ip')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'user', 'environment', 'is_active', 'expires_at')
        }),
        ('Scopes & Security Controls', {
            'fields': ('scopes', 'allowed_ips', 'rate_limit'),
        }),
        ('Webhooks Integration', {
            'fields': ('webhook_url', 'webhook_secret'),
        }),
        ('Cryptographic Details', {
            'fields': ('prefix', 'hashed_key'),
            'classes': ('collapse',),
        }),
        ('Usage Metadata', {
            'fields': ('created_at', 'last_used_at', 'last_ip'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change: # Only on creation
            raw_key, instance = APIKey.generate_key(
                name=obj.name,
                user=obj.user,
                environment=obj.environment,
                scopes=obj.scopes or None,
                webhook_url=obj.webhook_url or None,
                allowed_ips=obj.allowed_ips or None,
                expires_at=obj.expires_at
            )
            messages.success(
                request, 
                format_html(
                    "API Key created successfully! <br><br> "
                    "<strong>RAW SECRET KEY:</strong> <code style='background: #f4f4f4; padding: 4px 8px; border-radius: 4px; border: 1px solid #ddd; font-weight: bold;'>{}</code> <br><br> "
                    "<strong>WEBHOOK SECRET:</strong> <code style='background: #f4f4f4; padding: 4px 8px; border-radius: 4px; border: 1px solid #ddd;'>{}</code> <br><br> "
                    "Please copy these credentials now. The secret key will <strong>NEVER</strong> be shown again.",
                    raw_key,
                    instance.webhook_secret or 'N/A'
                )
            )
        else:
            super().save_model(request, obj, form, change)
