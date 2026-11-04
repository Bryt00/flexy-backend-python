from rest_framework import authentication
from rest_framework import exceptions
from django.utils import timezone
from django.core.cache import cache
from .models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    High-throughput, low-latency API Key authentication.
    Uses SHA-256 constant-time comparison, Redis key caching, and throttled DB updates.
    """
    def authenticate(self, request):
        api_key_str = request.META.get('HTTP_X_API_KEY')
        if not api_key_str:
            return None

        # Accept formats:
        # fx_live_<prefix>_<secret>
        # fx_test_<prefix>_<secret>
        # fx_<prefix>_<secret> (legacy)
        parts = api_key_str.split('_')
        if len(parts) < 3 or parts[0] != 'fx':
            raise exceptions.AuthenticationFailed('Invalid API Key format. Expected fx_<env>_<prefix>_<secret> or fx_<prefix>_<secret>')

        if parts[1] in ('live', 'test') and len(parts) >= 4:
            prefix = f"{parts[1]}_{parts[2]}"
        else:
            prefix = parts[1]

        # Fast cache lookup for key ID to avoid DB roundtrips on high throughput
        cache_key = f"auth_apikey_id:{prefix}"
        cached_id = cache.get(cache_key)

        api_key = None
        if cached_id:
            try:
                api_key = APIKey.objects.select_related('user').get(id=cached_id, is_active=True)
            except APIKey.DoesNotExist:
                cache.delete(cache_key)

        if not api_key:
            try:
                api_key = APIKey.objects.select_related('user').get(prefix=prefix, is_active=True)
                cache.set(cache_key, str(api_key.id), timeout=300)
            except APIKey.DoesNotExist:
                raise exceptions.AuthenticationFailed('Invalid or inactive API Key')

        # Fast verification (SHA-256 constant-time, fallback to legacy PBKDF2)
        if not api_key.verify_key(api_key_str):
            raise exceptions.AuthenticationFailed('Invalid API Key secret')

        # Extract client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')

        # Check IP whitelist (if configured for this key)
        if not api_key.is_ip_allowed(client_ip):
            raise exceptions.AuthenticationFailed(f'Client IP {client_ip} is not permitted for this API Key')

        # Throttled DB write: update last_used_at and last_ip at most once every 5 minutes
        now = timezone.now()
        should_update = (
            api_key.last_used_at is None or 
            (now - api_key.last_used_at).total_seconds() > 300 or 
            api_key.last_ip != client_ip
        )
        if should_update:
            api_key.last_used_at = now
            api_key.last_ip = client_ip
            api_key.save(update_fields=['last_used_at', 'last_ip'])

        # Return (user, auth) where auth is the APIKey instance so views can check scopes
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return 'X-Api-Key'
