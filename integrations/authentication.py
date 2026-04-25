from rest_framework import authentication
from rest_framework import exceptions
from django.utils import timezone
from .models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        api_key_str = request.META.get('HTTP_X_API_KEY')
        if not api_key_str:
            return None

        # Format: fx_prefix_secret
        parts = api_key_str.split('_')
        if len(parts) != 3 or parts[0] != 'fx':
            raise exceptions.AuthenticationFailed('Invalid API Key format')

        prefix = parts[1]
        try:
            api_key = APIKey.objects.get(prefix=prefix, is_active=True)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid or inactive API Key')

        if not api_key.verify_key(api_key_str):
            raise exceptions.AuthenticationFailed('Invalid API Key secret')

        # Update last used info
        api_key.last_used_at = timezone.now()
        # Try to get IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            api_key.last_ip = x_forwarded_for.split(',')[0].strip()
        else:
            api_key.last_ip = request.META.get('REMOTE_ADDR')
            
        api_key.save(update_fields=['last_used_at', 'last_ip'])

        return (api_key.user, None)

    def authenticate_header(self, request):
        return 'X-Api-Key'
