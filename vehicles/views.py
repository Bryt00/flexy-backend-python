from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Vehicle
from .serializers import VehicleSerializer
from profiles.models import Profile

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Allow drivers to only see their own vehicles
        if self.request.user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(driver__user=self.request.user)

    def perform_create(self, serializer):
        # Automatically link the vehicle to the logged-in user's profile
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(driver=profile)

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

    def create(self, request, *args, **kwargs):
        # The mobile app sends 'driverId' in the JSON, but our model uses 'driver' (FK)
        # perform_create handles the linkage, so we just remove driverId if present
        # to avoid serializer validation errors if 'driver' is missing.
        data = request.data.copy()
        if 'driverId' in data:
            data.pop('driverId')
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
