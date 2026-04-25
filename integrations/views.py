from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import APIKey
from .serializers import (
    APIKeySerializer, 
    APIKeyCreateSerializer, 
    APIKeyCreateResponseSerializer
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
        # Users can only see/manage their own keys
        return self.queryset.filter(user=self.request.user, is_active=True)

    @extend_schema(
        request=APIKeyCreateSerializer,
        responses={201: APIKeyCreateResponseSerializer},
        description="Creates a new API Key. The raw 'raw_key' is returned ONLY ONCE."
    )
    def create(self, request, *args, **kwargs):
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        raw_key, instance = APIKey.generate_key(
            name=serializer.validated_data['name'],
            user=request.user,
            expires_at=serializer.validated_data.get('expires_at')
        )

        return Response({
            'id': instance.id,
            'name': instance.name,
            'prefix': instance.prefix,
            'raw_key': raw_key,
            'message': 'Please copy this key now. It will NEVER be shown again.'
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        # Soft delete: just deactivate the key
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
