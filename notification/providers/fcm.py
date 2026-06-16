import firebase_admin
from firebase_admin import messaging
from notification.models import FCMDevice
from .base import PushNotificationProvider

class FCMProvider(PushNotificationProvider):
    def send_push(self, user_id, title, message, data=None, android_channel_id=None, android_sound=None, ios_sound=None):
        devices = FCMDevice.objects.filter(user_id=user_id)
        if not devices.exists():
            return False

        # Ensure we only send a DATA payload, not a Notification payload.
        # This prevents the OS from natively displaying it and allows the Flutter app to handle it silently
        # and render the custom UI widget.
        payload_data = data or {}
        payload_data.update({
            'title': str(title),
            'body': str(message),
        })
        
        # All values in data payload must be strings for FCM
        payload_data = {str(k): str(v) for k, v in payload_data.items()}

        fcm_message = messaging.MulticastMessage(
            data=payload_data,
            tokens=[device.registration_id for device in devices]
        )
        
        try:
            response = messaging.send_multicast(fcm_message)
            # Handle failures (e.g., token expired)
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        # If NotRegistered, delete the stale token
                        if resp.exception.code == 'messaging/registration-token-not-registered':
                            devices[idx].delete()
            return True
        except Exception as e:
            print(f"FCM Multicast Error: {e}")
            return False

    def send_broadcast(self, target_segment, title, message, data=None):
        # We can implement broadcasting using FCM Topics later
        # Currently, target_segment can map to a topic
        pass
