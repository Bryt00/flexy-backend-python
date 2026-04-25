from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from .models import Ride
from .serializers import RideSerializer

@receiver(post_save, sender=Ride)
def broadcast_ride_update(sender, instance, created, **kwargs):
    """
    Broadcasts ride updates to the specific ride group whenever a Ride instance is saved.
    This ensures real-time updates for status changes, driver assignments, and location tracking.
    """
    channel_layer = get_channel_layer()
    ride_data = RideSerializer(instance).data
    group_name = f'ride_{instance.id}'
    
    from asgiref.sync import async_to_sync
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'ride_update',
            'event_type': 'ride_status_update',
            'data': ride_data
        }
    )
@receiver(post_save, sender=Ride)
def cleanup_ride_chat(sender, instance, **kwargs):
    """
    Purges all chat messages when a ride is completed or cancelled.
    This fulfills the ephemeral chat requirement for active session temporary storage.
    """
    if instance.status in ['completed', 'cancelled']:
        from .models import ChatMessage
        msg_count = ChatMessage.objects.filter(ride=instance).count()
        if msg_count > 0:
            ChatMessage.objects.filter(ride=instance).delete()
            print(f"Purged {msg_count} ephemeral messages for concluding Ride {instance.id}")
