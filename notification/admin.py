from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Notification, Campaign
from .tasks import send_campaign_task

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__email', 'title', 'body')
    readonly_fields = ('created_at',)

@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('title', 'target_audience', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'target_audience', 'created_at')
    search_fields = ('title', 'body')
    actions = ['send_campaign']

    def send_campaign(self, request, queryset):
        for campaign in queryset:
            if campaign.status == 'SENT':
                self.message_user(request, f"Campaign '{campaign.title}' was already sent.", level='warning')
                continue
            
            # Trigger background task with Celery fallback
            celery_running = False
            try:
                from celery import current_app
                insp = current_app.control.inspect()
                if insp and insp.stats():
                    celery_running = True
            except Exception:
                pass

            if celery_running:
                send_campaign_task.delay(str(campaign.id))
            else:
                import threading
                threading.Thread(target=send_campaign_task, args=(str(campaign.id),), daemon=True).start()
            
        self.message_user(request, f"Started sending {queryset.count()} campaign(s) in the background.")
    
    send_campaign.short_description = "🚀 Broadcast to selected audience"
