from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import SiteSetting, DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType, VehicleCategory, ServiceArea
from .serializers import SiteSettingSerializer, DeliveryCategorySerializer, DeliveryWeightTierSerializer, DeliveryVehicleTypeSerializer, VehicleCategorySerializer, ServiceAreaSerializer
from core_auth.cache_utils import conditional_api_response, cached_api_response

class AdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

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

class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceArea.objects.filter(is_active=True)
    serializer_class = ServiceAreaSerializer
    permission_classes = [permissions.AllowAny]

class VehicleCategoryViewSet(viewsets.ModelViewSet):
    queryset = VehicleCategory.objects.all().order_by('slug')
    serializer_class = VehicleCategorySerializer
    permission_classes = [AdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        """Cache the full category list globally for 30 minutes.
        Invalidated automatically when a new category is saved via the admin (signal not required;
        the next request after 30 min will fetch fresh data)."""
        return cached_api_response(
            request,
            prefix='vehicle_categories',
            timeout=1800,
            fetcher=lambda: super(VehicleCategoryViewSet, self).list(request, *args, **kwargs),
            per_user=False,
            global_cache=True,
        )

