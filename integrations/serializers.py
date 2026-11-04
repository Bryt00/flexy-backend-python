from rest_framework import serializers
from .models import APIKey, AVAILABLE_SCOPES, DEFAULT_SCOPES

class ScopeItemSerializer(serializers.Serializer):
    scope = serializers.CharField()
    description = serializers.CharField()

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'environment', 'prefix', 'scopes',
            'allowed_ips', 'rate_limit', 'webhook_url', 'webhook_secret',
            'is_active', 'created_at', 'expires_at', 'last_used_at', 'last_ip'
        ]
        read_only_fields = [
            'id', 'prefix', 'webhook_secret', 'is_active', 
            'created_at', 'last_used_at', 'last_ip'
        ]

class APIKeyCreateSerializer(serializers.ModelSerializer):
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=DEFAULT_SCOPES,
        help_text="List of permitted scopes"
    )
    allowed_ips = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional IP / CIDR whitelist"
    )

    class Meta:
        model = APIKey
        fields = [
            'name', 'environment', 'scopes', 'allowed_ips', 
            'rate_limit', 'webhook_url', 'expires_at'
        ]

class APIKeyCreateResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    environment = serializers.CharField()
    prefix = serializers.CharField()
    scopes = serializers.ListField(child=serializers.CharField())
    webhook_url = serializers.URLField(allow_null=True)
    webhook_secret = serializers.CharField(allow_null=True)
    raw_key = serializers.CharField()
    message = serializers.CharField(default="Please copy this key now. It will NEVER be shown again.")

class APIKeyRotateResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    prefix = serializers.CharField()
    raw_key = serializers.CharField()
    message = serializers.CharField(default="Secret key rotated successfully. Copy the new key now.")

class TestWebhookRequestSerializer(serializers.Serializer):
    event_type = serializers.CharField(default="ping", required=False)
    sample_data = serializers.DictField(required=False, default=dict)

class TestWebhookResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    status_code = serializers.IntegerField(allow_null=True)
    latency_ms = serializers.IntegerField()
    body = serializers.CharField(allow_blank=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)
