from channels_redis.core import RedisChannelLayer
from .channel_serializer import UUIDMessagePackSerializer

class UUIDRedisChannelLayer(RedisChannelLayer):
    """
    A custom Redis Channel Layer that uses UUIDMessagePackSerializer 
    to handle UUID objects in messages.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uuid_serializer = UUIDMessagePackSerializer()

    def serialize(self, message):
        """
        Overwritten to use our custom UUID-aware serializer.
        """
        return self._uuid_serializer.serialize(message)

    def deserialize(self, message):
        """
        Overwritten to use our custom UUID-aware serializer.
        """
        return self._uuid_serializer.deserialize(message)
