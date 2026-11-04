from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .models import APIKey, AVAILABLE_SCOPES, DEFAULT_SCOPES
from .serializers import (
    APIKeySerializer, 
    APIKeyCreateSerializer, 
    APIKeyCreateResponseSerializer,
    APIKeyRotateResponseSerializer,
    TestWebhookRequestSerializer,
    TestWebhookResponseSerializer
)
from .webhooks import WebhookService


@extend_schema_view(
    list=extend_schema(
        tags=['Integrations'],
        summary='List my API keys',
        description='Returns all active API keys created by the authenticated developer/service account.',
    ),
    retrieve=extend_schema(
        tags=['Integrations'],
        summary='Get API key details',
        description='Returns details of a specific API key (masked secret).',
    ),
    destroy=extend_schema(
        tags=['Integrations'],
        summary='Revoke an API key',
        description='Soft-deletes/deactivates an API key. Once deactivated, calls with this key will return `401 Unauthorized`.',
        responses={204: OpenApiResponse(description='API key deactivated successfully.')},
    ),
)
class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for self-service API Key management.
    API Keys are used by external services to integrate with our system.
    """
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') == 'admin':
            user_id = self.request.query_params.get('user_id')
            if user_id:
                return self.queryset.filter(user_id=user_id, is_active=True)
            return self.queryset.filter(is_active=True)
        return self.queryset.filter(user=user, is_active=True)

    @extend_schema(
        tags=['Integrations'],
        summary='Create a new API key',
        request=APIKeyCreateSerializer,
        responses={201: APIKeyCreateResponseSerializer},
        description=(
            'Generates a new self-service API key for external integrations.\n\n'
            '**CRITICAL:** The raw unhashed key (`raw_key`) is returned **ONLY ONCE** in this response. '
            'It cannot be retrieved again later. The user must save it immediately.'
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        raw_key, instance = APIKey.generate_key(
            name=serializer.validated_data['name'],
            user=request.user,
            environment=serializer.validated_data.get('environment', 'LIVE'),
            scopes=serializer.validated_data.get('scopes'),
            webhook_url=serializer.validated_data.get('webhook_url'),
            allowed_ips=serializer.validated_data.get('allowed_ips'),
            expires_at=serializer.validated_data.get('expires_at')
        )

        return Response({
            'id': instance.id,
            'name': instance.name,
            'environment': instance.environment,
            'prefix': instance.prefix,
            'scopes': instance.scopes,
            'webhook_url': instance.webhook_url,
            'webhook_secret': instance.webhook_secret,
            'raw_key': raw_key,
            'message': 'Please copy this key now. It will NEVER be shown again.'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Integrations'],
        summary='Rotate an API key secret',
        responses={200: APIKeyRotateResponseSerializer},
        description='Regenerates the raw secret and prefix for an existing API key while preserving its ID and configuration.'
    )
    @action(detail=True, methods=['post'], url_path='rotate')
    def rotate(self, request, pk=None):
        instance = self.get_object()
        old_prefix = instance.prefix
        new_raw_key = instance.rotate_secret()
        
        # Evict old cache entry
        cache.delete(f"auth_apikey_id:{old_prefix}")

        return Response({
            'id': instance.id,
            'prefix': instance.prefix,
            'raw_key': new_raw_key,
            'message': 'Secret key rotated successfully. Copy the new key now.'
        })

    @extend_schema(
        tags=['Integrations'],
        summary='Test webhook endpoint',
        request=TestWebhookRequestSerializer,
        responses={200: TestWebhookResponseSerializer},
        description='Dispatches a test HMAC-signed event to the key\'s configured webhook URL.'
    )
    @action(detail=True, methods=['post'], url_path='test-webhook')
    def test_webhook(self, request, pk=None):
        instance = self.get_object()
        if not instance.webhook_url:
            return Response(
                {'error': 'No webhook URL configured for this API key.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        req_serializer = TestWebhookRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        event_type = req_serializer.validated_data.get('event_type') or 'ping'
        sample_data = req_serializer.validated_data.get('sample_data') or {
            'message': 'FlexyRide Webhook Test Verification',
            'api_key_id': str(instance.id),
            'environment': instance.environment
        }

        result = WebhookService.send_event(
            webhook_url=instance.webhook_url,
            secret=instance.webhook_secret or '',
            event_type=event_type,
            data=sample_data
        )

        return Response(result)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        # Evict from cache immediately
        cache.delete(f"auth_apikey_id:{instance.prefix}")
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Integrations'],
    summary='List available integration scopes',
    description='Returns all supported permission scopes and descriptions.'
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def list_available_scopes(request):
    scopes = [{'scope': s[0], 'description': s[1]} for s in AVAILABLE_SCOPES]
    return Response({
        'scopes': scopes,
        'default_scopes': DEFAULT_SCOPES
    })
