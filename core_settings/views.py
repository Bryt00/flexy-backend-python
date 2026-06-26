from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import SiteSetting, DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType
from .serializers import SiteSettingSerializer, DeliveryCategorySerializer, DeliveryWeightTierSerializer, DeliveryVehicleTypeSerializer
from core_auth.cache_utils import conditional_api_response

class SiteSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows site settings to be viewed.
    """
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)

class DeliveryCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryCategory.objects.filter(is_active=True)
    serializer_class = DeliveryCategorySerializer
    permission_classes = [permissions.AllowAny]

class DeliveryWeightTierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryWeightTier.objects.filter(is_active=True)
    serializer_class = DeliveryWeightTierSerializer
    permission_classes = [permissions.AllowAny]

class DeliveryVehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryVehicleType.objects.filter(is_active=True)
    serializer_class = DeliveryVehicleTypeSerializer
    permission_classes = [permissions.AllowAny]
