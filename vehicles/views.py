from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Vehicle
from .serializers import VehicleSerializer
from profiles.models import Profile
from core_auth.cache_utils import cached_api_response, invalidate_user_cache

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse


@extend_schema_view(
    list=extend_schema(
        tags=['Vehicles'],
        summary='List my vehicles',
        description=(
            'Returns all vehicles belonging to the authenticated driver.\n\n'
            'Staff/admin users see all vehicles in the system. Response is cached for 5 minutes.'
        ),
    ),
    retrieve=extend_schema(
        tags=['Vehicles'],
        summary='Get vehicle details',
        description='Returns full details for a specific vehicle by ID.',
    ),
    create=extend_schema(
        tags=['Vehicles'],
        summary='Register or update a vehicle',
        description=(
            'Registers a new vehicle for the authenticated driver.\n\n'
            '**Upsert behaviour:** If the driver already has a vehicle, the existing one is updated instead '
            'of creating a duplicate. This simplifies the Flutter app flow.\n\n'
            'The vehicle is automatically linked to the driver\'s profile — no need to send `driverId`.'
        ),
    ),
    update=extend_schema(
        tags=['Vehicles'],
        summary='Update a vehicle',
        description=(
            'Fully updates a vehicle record.\n\n'
            '**Online restriction:** Setting `status=available` requires an active subscription. '
            'Returns a validation error if the subscription is due or expired.'
        ),
    ),
    partial_update=extend_schema(
        tags=['Vehicles'],
        summary='Partially update a vehicle',
        description='Partially updates a vehicle record.',
    ),
    destroy=extend_schema(
        tags=['Vehicles'],
        summary='Delete a vehicle',
        description='Removes a vehicle registration from the system.',
    ),
)
class VehicleViewSet(viewsets.ModelViewSet):
    """Driver vehicle registration and management."""
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Allow drivers to only see their own vehicles
        if self.request.user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(driver__user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Cache vehicles list per user."""
        def fetch_vehicles():
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return cached_api_response(request, 'vehicles', timeout=300, fetcher=fetch_vehicles)

    def perform_create(self, serializer):
        # Automatically link the vehicle to the logged-in user's profile
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(driver=profile)
        invalidate_user_cache(self.request.user.id, 'vehicles')

    def perform_update(self, serializer):
        # Prevent going online if subscription is due or expired
        new_status = self.request.data.get('status')
        if new_status == 'available':
            profile = getattr(self.request.user, 'profile', None)
            if profile:
                # Check subscription eligibility
                has_subscription = hasattr(profile, 'subscription')
                if not has_subscription or not profile.subscription.can_go_online:
                    from rest_framework.exceptions import ValidationError
                    
                    msg = "Your subscription is due. Please renew to go online."
                    if has_subscription and profile.subscription.is_in_grace_period:
                        remaining = profile.subscription.grace_period_remaining
                        msg = f"Subscription due. You have {remaining} to renew to stay visible."
                    
                    raise ValidationError({"status": msg})
        
        serializer.save()
        invalidate_user_cache(self.request.user.id, 'vehicles')

    def create(self, request, *args, **kwargs):
        # The mobile app sends 'driverId' in the JSON, but our model uses 'driver' (FK)
        data = request.data.copy()
        if 'driverId' in data:
            data.pop('driverId')
        
        profile = Profile.objects.get(user=request.user)
        existing_vehicle = Vehicle.objects.filter(driver=profile).first()

        if existing_vehicle:
            serializer = self.get_serializer(existing_vehicle, data=data, partial=True)
        else:
            serializer = self.get_serializer(data=data)

        if not serializer.is_valid():
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Vehicle registration validation error for user {request.user.id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if existing_vehicle:
            serializer.save()
        else:
            self.perform_create(serializer)

        invalidate_user_cache(request.user.id, 'vehicles')
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if existing_vehicle else status.HTTP_201_CREATED,
            headers=headers,
        )
