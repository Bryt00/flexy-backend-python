from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import SiteSetting, DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType, VehicleCategory, ServiceArea, AppVersion
from .serializers import (
    SiteSettingSerializer, DeliveryCategorySerializer, DeliveryWeightTierSerializer, 
    DeliveryVehicleTypeSerializer, VehicleCategorySerializer, ServiceAreaSerializer, AppVersionSerializer
)
from core_auth.cache_utils import conditional_api_response, cached_api_response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse

class AdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List site settings', description='Returns public key-value platform settings.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get site setting by key', description='Returns a specific setting by key.'),
)
class SiteSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows site settings to be viewed."""
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List delivery item categories', description='Returns active courier delivery item categories (document, parcel, food, etc.). Cached 30m globally.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get delivery category details', description='Returns details of a specific delivery category.'),
)
class DeliveryCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryCategory.objects.filter(is_active=True)
    serializer_class = DeliveryCategorySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        return cached_api_response(
            request, prefix='delivery_categories', timeout=1800,
            fetcher=lambda: super(DeliveryCategoryViewSet, self).list(request, *args, **kwargs),
            per_user=False, global_cache=True
        )


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List delivery weight tiers', description='Returns active courier weight tiers (0-5kg, 5-15kg, etc.). Cached 30m globally.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get weight tier details', description='Returns details of a specific weight tier.'),
)
class DeliveryWeightTierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryWeightTier.objects.filter(is_active=True)
    serializer_class = DeliveryWeightTierSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        return cached_api_response(
            request, prefix='delivery_weight_tiers', timeout=1800,
            fetcher=lambda: super(DeliveryWeightTierViewSet, self).list(request, *args, **kwargs),
            per_user=False, global_cache=True
        )


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List delivery vehicle types', description='Returns active delivery vehicle types (motorbike, van, truck). Cached 30m globally.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get delivery vehicle type details', description='Returns details of a specific delivery vehicle type.'),
)
class DeliveryVehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryVehicleType.objects.filter(is_active=True)
    serializer_class = DeliveryVehicleTypeSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        return cached_api_response(
            request, prefix='delivery_vehicle_types', timeout=1800,
            fetcher=lambda: super(DeliveryVehicleTypeViewSet, self).list(request, *args, **kwargs),
            per_user=False, global_cache=True
        )


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List service areas', description='Returns active geographic service polygons/boundaries. Cached 30m globally.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get service area details', description='Returns details of a specific service area.'),
)
class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceArea.objects.filter(is_active=True)
    serializer_class = ServiceAreaSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        return cached_api_response(
            request, prefix='service_areas', timeout=1800,
            fetcher=lambda: super(ServiceAreaViewSet, self).list(request, *args, **kwargs),
            per_user=False, global_cache=True
        )


@extend_schema_view(
    list=extend_schema(tags=['Settings'], summary='List vehicle categories', description='Returns all vehicle pricing categories (go, standard, comfort, luxury, delivery). Cached 30m globally.'),
    retrieve=extend_schema(tags=['Settings'], summary='Get vehicle category details', description='Returns details of a specific vehicle category.'),
    create=extend_schema(tags=['Settings'], summary='Create vehicle category', description='Admin-only. Creates a new vehicle category.'),
    update=extend_schema(tags=['Settings'], summary='Update vehicle category', description='Admin-only. Updates a vehicle category.'),
    partial_update=extend_schema(tags=['Settings'], summary='Partially update vehicle category', description='Admin-only.'),
    destroy=extend_schema(tags=['Settings'], summary='Delete vehicle category', description='Admin-only.'),
)
class VehicleCategoryViewSet(viewsets.ModelViewSet):
    queryset = VehicleCategory.objects.all().order_by('slug')
    serializer_class = VehicleCategorySerializer
    permission_classes = [AdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        return cached_api_response(
            request,
            prefix='vehicle_categories',
            timeout=1800,
            fetcher=lambda: super(VehicleCategoryViewSet, self).list(request, *args, **kwargs),
            per_user=False,
            global_cache=True,
        )


@extend_schema_view(
    list=extend_schema(
        tags=['Settings'],
        summary='Check app version requirements',
        description=(
            'Returns min required version and latest available version for mobile app update checks.\n\n'
            'Filter by `platform` (`android`/`ios`) and `app_type` (`PASSENGER`/`DRIVER`).'
        ),
        parameters=[
            OpenApiParameter(name='platform', type=str, location='query', required=False, description='Platform filter: android or ios.'),
            OpenApiParameter(name='app_type', type=str, location='query', required=False, description='App type filter: PASSENGER or DRIVER.'),
        ],
    ),
    retrieve=extend_schema(tags=['Settings'], summary='Get app version record', description='Returns a specific app version record.'),
)
class AppVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows checking app version requirements."""
    queryset = AppVersion.objects.all()
    serializer_class = AppVersionSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        platform = request.query_params.get('platform')
        app_type = request.query_params.get('app_type')
        
        queryset = self.get_queryset()
        if platform:
            queryset = queryset.filter(platform=platform)
        if app_type:
            queryset = queryset.filter(app_type=app_type)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
