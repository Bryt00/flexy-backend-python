from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import importlib
from django.conf import settings
from .models import Notification

def get_push_provider():
    provider_path = getattr(settings, 'ACTIVE_PUSH_PROVIDER', None)
    if provider_path:
        module_name, class_name = provider_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        provider_class = getattr(module, class_name)
        return provider_class()
    return None

def send_notification(user, title, body, type='PUSH', ref_id=None, android_channel_id=None, android_sound=None, ios_sound=None):
    """
    Sends a notification to a specific user.
    1. Saves the notification to the database.
    2. Broadcasts the notification via WebSockets for real-time delivery.
    3. If type='PUSH', sends a remote push via the active Push Provider.
    """
    # 1. Create database record
    notification = Notification.objects.create(
        user=user,
        title=title if isinstance(title, str) else title.get('en', 'Notification'),
        body=body if isinstance(body, str) else body.get('en', 'You have a new notification.'),
        type=type
    )

    # 2. Remote Push via Provider
    if type == 'PUSH':
        data = {'ref_id': str(ref_id)} if ref_id else {}
        from .tasks import send_fcm_push_task
        
        celery_running = False
        try:
            from celery import current_app
            insp = current_app.control.inspect()
            if insp and insp.stats():
                celery_running = True
        except Exception:
            pass

        if celery_running:
            send_fcm_push_task.delay(
                user_id=str(user.id),
                title=title if isinstance(title, str) else title.get('en', 'Notification'),
                message=body if isinstance(body, str) else body.get('en', 'You have a new notification.'),
                data=data
            )
        else:
            import threading
            threading.Thread(
                target=send_fcm_push_task,
                args=(
                    str(user.id),
                    title if isinstance(title, str) else title.get('en', 'Notification'),
                    body if isinstance(body, str) else body.get('en', 'You have a new notification.'),
                    data
                ),
                daemon=True
            ).start()

    # 2. Broadcast via WebSockets
    channel_layer = get_channel_layer()
    group_name = f'notifications_{user.id}'
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'notification': {
                'id': str(notification.id),
                'title': title,
                'message': body,
                'type': type.lower(),
                'ref_id': str(ref_id) if ref_id else None,
                'created_at': notification.created_at.isoformat(),
            }
        }
    )
    
    return notification
