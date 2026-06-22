import requests
import logging
from django.conf import settings
from .base import PushNotificationProvider

logger = logging.getLogger(__name__)

class OneSignalProvider(PushNotificationProvider):
    def __init__(self):
        self.app_id = getattr(settings, 'ONESIGNAL_APP_ID', None)
        self.api_key = getattr(settings, 'ONESIGNAL_REST_API_KEY', None)
        self.base_url = 'https://onesignal.com/api/v1/notifications'

    def send_push(self, user_id: str, title, message, data: dict = None, android_channel_id: str = None, android_sound: str = None, ios_sound: str = None, app_type: str = None) -> bool:
        if not self.app_id or not self.api_key:
            logger.warning("OneSignalProvider: ONESIGNAL_APP_ID or ONESIGNAL_REST_API_KEY is not set.")
            return False

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': f'Basic {self.api_key}'
        }

        headings = title if isinstance(title, dict) else {'en': title}
        contents = message if isinstance(message, dict) else {'en': message}

        payload = {
            'app_id': self.app_id,
            'include_external_user_ids': [str(user_id)],
            'headings': headings,
            'contents': contents,
            'channel_for_external_user_ids': 'push'
        }
        
        if data:
            payload['data'] = data
            
        if android_channel_id:
            payload['android_channel_id'] = android_channel_id
        if android_sound:
            payload['android_sound'] = android_sound
        if ios_sound:
            payload['ios_sound'] = ios_sound

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response_data = response.json()
            if response.status_code == 200 and 'errors' not in response_data:
                return True
            else:
                logger.error(f"OneSignalProvider Error: {response_data}")
                return False
        except Exception as e:
            logger.error(f"OneSignalProvider Exception: {str(e)}")
            return False
