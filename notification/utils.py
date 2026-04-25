from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

def send_notification(user, title, body, type='PUSH', ref_id=None):
    """
    Sends a notification to a specific user.
    1. Saves the notification to the database.
    2. Broadcasts the notification via WebSockets for real-time delivery.
    """
    # 1. Create database record
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        type=type
    )

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
