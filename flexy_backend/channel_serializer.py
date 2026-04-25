import uuid
import msgpack
import logging

logger = logging.getLogger(__name__)

class UUIDMessagePackSerializer:
    """
    Custom serializer for Django Channels that handles UUID objects.
    Ensures that any UUID encountered in the message dictionary is 
    automatically converted to a string before binary packing.
    """

    @staticmethod
    def pack_default(obj):
        """
        Default handler for objects that msgpack doesn't recognize.
        """
        if isinstance(obj, uuid.UUID):
            return str(obj)
        # Add other custom types here if needed (e.g. decimal, datetime)
        return str(obj)

    def serialize(self, message):
        """
        Serializes a message dictionary to binary msgpack format.
        """
        try:
            return msgpack.packb(message, default=self.pack_default, use_bin_type=True)
        except Exception as e:
            logger.error(f"UUIDMessagePackSerializer: Serialization failed: {e}")
            raise e

    def deserialize(self, message):
        """
        Deserializes binary msgpack format back to a Python dictionary.
        """
        try:
            return msgpack.unpackb(message, raw=False)
        except Exception as e:
            logger.error(f"UUIDMessagePackSerializer: Deserialization failed: {e}")
            raise e
