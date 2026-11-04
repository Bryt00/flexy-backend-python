import uuid
import secrets
import hashlib
import hmac
import ipaddress
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

AVAILABLE_SCOPES = [
    ('deliveries:estimate', 'Calculate courier & parcel delivery estimates'),
    ('deliveries:create', 'Create new courier & parcel delivery orders'),
    ('deliveries:read', 'View delivery status and active tracking details'),
    ('deliveries:cancel', 'Cancel delivery orders'),
    ('rides:estimate', 'Calculate ride-hailing fares and route ETAs'),
    ('rides:create', 'Request on-demand and scheduled rides'),
    ('rides:read', 'View ride status and telemetry tracking'),
    ('rides:cancel', 'Cancel rides'),
    ('wallet:read', 'View partner credit and transaction balance'),
    ('settings:read', 'Access operational zones and vehicle categories'),
    ('*', 'Full platform access (All scopes)'),
]

DEFAULT_SCOPES = [
    'deliveries:estimate',
    'deliveries:create',
    'deliveries:read',
    'rides:estimate',
    'rides:create',
    'rides:read',
    'settings:read'
]

class APIKey(models.Model):
    ENVIRONMENT_CHOICES = [
        ('LIVE', 'Live / Production'),
        ('SANDBOX', 'Sandbox / Test'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='api_keys',
        help_text="The user/service account associated with this key"
    )
    name = models.CharField(max_length=255, help_text="A descriptive name for this service/integration")
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='LIVE', db_index=True)
    prefix = models.CharField(max_length=16, unique=True, editable=False, db_index=True)
    hashed_key = models.CharField(max_length=255, editable=False)
    
    # Scoping & Access Control
    scopes = models.JSONField(default=list, blank=True, help_text="List of granted permission scopes")
    allowed_ips = models.JSONField(default=list, blank=True, help_text="Optional CIDR or IP whitelist for enterprise access")
    rate_limit = models.CharField(max_length=50, default='10000/day', help_text="Rate limit quota")

    # Webhook Integration
    webhook_url = models.URLField(max_length=500, null=True, blank=True, help_text="Outbound webhook endpoint for real-time lifecycle events")
    webhook_secret = models.CharField(max_length=128, null=True, blank=True, editable=False, help_text="HMAC secret used to sign outbound webhooks")

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.environment}] ({self.prefix}...)"

    @classmethod
    def hash_raw_key(cls, raw_key: str) -> str:
        """
        Fast cryptographic SHA-256 hash. High-entropy API keys (256-bit) do not need
        slow KDFs like PBKDF2/bcrypt, saving 80ms CPU per request.
        """
        digest = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
        return f"sha256${digest}"

    @classmethod
    def generate_key(cls, name, user, environment='LIVE', scopes=None, webhook_url=None, allowed_ips=None, expires_at=None):
        """
        Generates a new API key, hashes it via SHA-256, generates a webhook secret,
        and returns the raw key. The raw key is returned only once.
        """
        hex_token = secrets.token_hex(4) # 8 chars
        secret = secrets.token_urlsafe(32) # high entropy
        env_tag = 'test' if environment == 'SANDBOX' else 'live'
        prefix = f"{env_tag}_{hex_token}"
        raw_key = f"fx_{prefix}_{secret}"
        
        hashed_key = cls.hash_raw_key(raw_key)
        webhook_secret = f"whsec_{secrets.token_urlsafe(24)}"

        if scopes is None:
            scopes = list(DEFAULT_SCOPES)
        if allowed_ips is None:
            allowed_ips = []

        instance = cls.objects.create(
            name=name,
            user=user,
            environment=environment,
            prefix=prefix,
            hashed_key=hashed_key,
            scopes=scopes,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            allowed_ips=allowed_ips,
            expires_at=expires_at
        )
        
        return raw_key, instance

    def rotate_secret(self):
        """
        Rotates the secret while keeping the same key metadata and ID.
        """
        hex_token = secrets.token_hex(4)
        secret = secrets.token_urlsafe(32)
        env_tag = 'test' if self.environment == 'SANDBOX' else 'live'
        new_prefix = f"{env_tag}_{hex_token}"
        new_raw_key = f"fx_{new_prefix}_{secret}"
        
        self.prefix = new_prefix
        self.hashed_key = self.hash_raw_key(new_raw_key)
        self.save(update_fields=['prefix', 'hashed_key'])
        return new_raw_key

    def verify_key(self, raw_key: str) -> bool:
        """
        Verifies the provided raw key. Supports fast constant-time SHA-256 comparison,
        with backward-compatibility fallback for legacy PBKDF2 keys.
        """
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
            
        if self.hashed_key.startswith('sha256$'):
            expected_digest = self.hashed_key.split('$', 1)[1]
            actual_digest = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
            return hmac.compare_digest(actual_digest, expected_digest)
        
        # Legacy fallback (Django PBKDF2/Argon2)
        return check_password(raw_key, self.hashed_key)

    def has_scope(self, scope_name: str) -> bool:
        """
        Checks whether this key possesses the required permission scope.
        Supports wildcards like '*' or 'deliveries:*'.
        """
        if not self.scopes:
            return False
        if '*' in self.scopes:
            return True
        if scope_name in self.scopes:
            return True
        # Check domain wildcard, e.g. "deliveries:*" matches "deliveries:create"
        if ':' in scope_name:
            domain = scope_name.split(':', 1)[0]
            if f"{domain}:*" in self.scopes:
                return True
        return False

    def is_ip_allowed(self, client_ip: str) -> bool:
        """
        Checks if client IP is permitted according to allowed_ips whitelist.
        If allowed_ips is empty, any IP is permitted.
        """
        if not self.allowed_ips or not client_ip:
            return True
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            for rule in self.allowed_ips:
                rule = str(rule).strip()
                if not rule:
                    continue
                if '/' in rule:
                    if ip_obj in ipaddress.ip_network(rule, strict=False):
                        return True
                elif client_ip == rule:
                    return True
            return False
        except ValueError:
            return False
