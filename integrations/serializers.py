from rest_framework import serializers
from .models import APIKey

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'prefix', 'is_active', 
            'created_at', 'expires_at', 'last_used_at'
        ]
        read_only_fields = ['id', 'prefix', 'created_at', 'last_used_at']

class APIKeyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['name', 'expires_at']

class APIKeyCreateResponseSerializer(serializers.Serializer):
    """
    Serializer used only for the create response to include the raw secret key.
    """
    id = serializers.UUIDField()
    name = serializers.CharField()
    prefix = serializers.CharField()
    raw_key = serializers.CharField()
    message = serializers.CharField(default="Please copy this key now. It will NEVER be shown again.")
