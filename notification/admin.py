from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Notification, Campaign

from .utils import send_notification
from django.utils import timezone

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__email', 'title', 'body')
    readonly_fields = ('created_at',)
    actions = ['send_mass_notification']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            try:
                send_notification(obj.user, obj.title, obj.body)
                obj.sent_at = timezone.now()
                obj.save()
            except Exception as e:
                self.message_user(request, f"Notification saved but push failed: {e}", level='error')

    def send_mass_notification(self, request, queryset):
        self.message_user(request, "Use the Campaigns section to send mass notifications to all users.", level='warning')
    
    send_mass_notification.short_description = "⚠️ To send to ALL users, use Campaigns instead"

@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('title', 'target_audience', 'target_city', 'target_condition', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'target_audience', 'target_condition', 'created_at')
    search_fields = ('title', 'body', 'target_city')
    fieldsets = (
        ('Content', {
            'fields': ('title', 'body', 'data_payload')
        }),
        ('Targeting', {
            'fields': ('target_audience', 'target_city', 'target_condition')
        }),
        ('Status', {
            'fields': ('status', 'sent_at')
        }),
    )
    actions = ['broadcast_push', 'broadcast_email']

    def broadcast_push(self, request, queryset):
        from .tasks import broadcast_campaign_push_task
        dispatched_count = 0
        for campaign in queryset:
            
            celery_running = False
            try:
                from celery import current_app
                insp = current_app.control.inspect()
                if insp and insp.stats():
                    celery_running = True
            except Exception:
                pass

            if celery_running:
                broadcast_campaign_push_task.delay(str(campaign.id))
            else:
                import threading
                threading.Thread(target=broadcast_campaign_push_task, args=(str(campaign.id),), daemon=True).start()
            
            dispatched_count += 1
            
        if dispatched_count > 0:
            self.message_user(request, f"Started sending Push Notifications for {dispatched_count} campaign(s) in the background.")
    
    broadcast_push.short_description = "📲 Broadcast Push Notifications"

    def broadcast_email(self, request, queryset):
        from .tasks import broadcast_campaign_email_task
        dispatched_count = 0
        for campaign in queryset:
            
            celery_running = False
            try:
                from celery import current_app
                insp = current_app.control.inspect()
                if insp and insp.stats():
                    celery_running = True
            except Exception:
                pass

            if celery_running:
                broadcast_campaign_email_task.delay(str(campaign.id))
            else:
                import threading
                threading.Thread(target=broadcast_campaign_email_task, args=(str(campaign.id),), daemon=True).start()
                
            dispatched_count += 1
            
        if dispatched_count > 0:
            self.message_user(request, f"Started sending Bulk Emails for {dispatched_count} campaign(s) in the background.")
    
    broadcast_email.short_description = "📧 Broadcast Bulk Emails"
