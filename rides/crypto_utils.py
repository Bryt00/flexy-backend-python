import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.encoding import force_bytes, force_str

class ChatEncryption:
    """
    Utility class for encrypting and decrypting chat messages at rest.
    Uses a key derived from the Django SECRET_KEY to ensure messages are 
    unreadable in the database.
    """
    
    _fernet = None

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            # Derive a 32-byte key from SECRET_KEY
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            cls._fernet = Fernet(base64.urlsafe_b64encode(key))
        return cls._fernet

    @classmethod
    def encrypt(cls, text):
        if not text:
            return text
        try:
            f = cls._get_fernet()
            return force_str(f.encrypt(force_bytes(text)))
        except Exception as e:
            print(f"Encryption error: {e}")
            return text

    @classmethod
    def decrypt(cls, encrypted_text):
        if not encrypted_text:
            return encrypted_text
        try:
            f = cls._get_fernet()
            return force_str(f.decrypt(force_bytes(encrypted_text)))
        except Exception:
            # Return original text if it's not encrypted or decryption fails
            return encrypted_text
