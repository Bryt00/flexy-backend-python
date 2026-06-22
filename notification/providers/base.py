from abc import ABC, abstractmethod

from typing import Union, Dict

class PushNotificationProvider(ABC):
    @abstractmethod
    def send_push(self, user_id: str, title: Union[str, Dict[str, str]], message: Union[str, Dict[str, str]], data: dict = None, android_channel_id: str = None, android_sound: str = None, ios_sound: str = None, app_type: str = None) -> bool:
        """
        Send a push notification to a specific user.
        :param user_id: The external user ID used to target the device.
        :param title: The title of the notification. Can be a string or dictionary of language codes (e.g. {'en': 'Hello', 'fr': 'Bonjour'}).
        :param message: The body of the notification. Can be a string or dictionary.
        :param data: Optional payload data.
        :param android_channel_id: Optional Android Notification Channel ID for custom sounds/priority.
        :param app_type: Optional app type to filter the push notification.
        :return: True if successfully sent, False otherwise.
        """
        pass
