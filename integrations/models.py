import uuid
import secrets
import hashlib
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='api_keys',
        help_text="The user/service account associated with this key"
    )
    name = models.CharField(max_length=255, help_text="A descriptive name for this service/integration")
    prefix = models.CharField(max_length=8, unique=True, editable=False)
    hashed_key = models.CharField(max_length=255, editable=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def generate_key(cls, name, user, expires_at=None):
        """
        Generates a new API key, saves the hash, and returns the raw key.
        The raw key is NEVER stored and is returned only once.
        """
        prefix = secrets.token_hex(4) # 8 chars
        secret = secrets.token_urlsafe(32) # high entropy secret
        raw_key = f"fx_{prefix}_{secret}"
        
        # We use Django's default hasher (PBKDF2/Argon2) for maximum robustness
        hashed_key = make_password(raw_key)
        
        instance = cls.objects.create(
            name=name,
            user=user,
            prefix=prefix,
            hashed_key=hashed_key,
            expires_at=expires_at
        )
        
        return raw_key, instance

    def verify_key(self, raw_key):
        """
        Verifies the provided raw key against the stored hash.
        """
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
            
        return check_password(raw_key, self.hashed_key)
