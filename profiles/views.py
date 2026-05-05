from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Profile, DriverVerification
from .serializers import ProfileSerializer, DriverVerificationSerializer
from drf_spectacular.utils import extend_schema, OpenApiTypes
from django.utils import timezone
from integrations.email_service import EmailService

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.action == 'me':
            try:
                return Profile.objects.get(user=self.request.user)
            except Profile.DoesNotExist:
                from rest_framework.exceptions import NotFound
                raise NotFound("Profile not found")
        return super().get_object()

    @extend_schema(responses={200: ProfileSerializer})
    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def me(self, request):
        if request.method == 'GET':
            try:
                profile = Profile.objects.get(user=request.user)
                serializer = self.get_serializer(profile)
                return Response(serializer.data)
            except Profile.DoesNotExist:
                return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses={200: ProfileSerializer})
    @action(detail=False, methods=['patch'])
    def preferences(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if 'notification_preferences' in request.data:
            profile.notification_preferences = request.data['notification_preferences']
        if 'is_2fa_enabled' in request.data:
            profile.is_2fa_enabled = request.data['is_2fa_enabled']
            
        profile.save()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @extend_schema(responses={200: DriverVerificationSerializer})
    @action(detail=False, methods=['get'], url_path='verification')
    def verification_status(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
        verification, created = DriverVerification.objects.get_or_create(driver=profile)
        serializer = DriverVerificationSerializer(verification)
        return Response(serializer.data)
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='verification/initiate')
    def initiate_verification(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
        verification, created = DriverVerification.objects.get_or_create(driver=profile)

        # --- Re-submission Guard ---
        # Prevent tampering: once submitted or verified, block further document changes.
        # Only allow re-submission if the previous attempt was rejected.
        if not created and verification.status in ('SUBMITTED', 'VERIFIED'):
            return Response({
                'error': 'Verification already submitted.',
                'detail': f'Your verification is currently {verification.status.lower()}. '
                          f'You cannot re-submit while it is under review or already approved.',
                'verification_status': verification.status,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mapping frontend keys to backend fields
        license_url = request.data.get('license_url', verification.license_url)
        id_card_url = request.data.get('id_card_url', verification.id_card_url)
        insurance_url = request.data.get('insurance_url', verification.insurance_url)
        roadworthy_url = request.data.get('roadworthy_url', verification.roadworthy_url)
        vehicle_video_url = request.data.get('vehicle_video_url', verification.vehicle_video_url)

        # PDF Validation for all docs except video
        docs_to_validate = {
            'License': license_url,
            'ID Card': id_card_url,
            'Insurance': insurance_url,
            'Roadworthy': roadworthy_url
        }
        
        for name, url in docs_to_validate.items():
            if url and not url.lower().endswith('.pdf'):
                return Response({
                    'error': f'Invalid file format for {name}. Only PDF files are allowed.',
                    'detail': f'The provided URL does not appear to be a PDF: {url}'
                }, status=status.HTTP_400_BAD_REQUEST)

        verification.license_url = license_url
        verification.id_card_url = id_card_url
        verification.insurance_url = insurance_url
        verification.roadworthy_url = roadworthy_url
        verification.vehicle_video_url = vehicle_video_url
        
        verification.status = 'SUBMITTED'
        verification.save()
        
        # Notify Admin
        EmailService.send_admin_verification_notification_email(
            driver_name=profile.full_name or request.user.email,
            driver_email=request.user.email
        )
        
        return Response({
            'status': 'Verification submitted', 
            'profile_id': profile.user_id,
            'verification_status': verification.status
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='tier-definitions')
    def tier_definitions(self, request):
        """Returns the available driver tiers and their required points."""
        return Response([
            {
                "name": "Silver",
                "min_points": 0,
                "description": "Welcome to FlexyPro! Earn points by completing rides and maintaining high ratings.",
                "benefits": []
            },
            {
                "name": "Gold",
                "min_points": 500,
                "description": "Consistent performer! You are among our top drivers.",
                "benefits": []
            },
            {
                "name": "Platinum",
                "min_points": 1500,
                "description": "Elite Status! You provide exceptional service to our riders.",
                "benefits": []
            }
        ])

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='location')
    def update_location(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            lat = request.data.get('lat')
            lng = request.data.get('lng')
            
            if lat is None or lng is None:
                return Response({"error": "lat and lng are required"}, status=status.HTTP_400_BAD_REQUEST)
                
            profile.last_lat = float(lat)
            profile.last_lng = float(lng)
            profile.last_location_update = timezone.now()
            profile.save()
            
            # Push to Redis for lightning fast spherical driver matching
            from flexy_backend.redis_client import redis_geo
            redis_geo.geo_add_driver(str(profile.pk), profile.last_lat, profile.last_lng)
            
            return Response({"status": "Location updated"}, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError) as e:
            return Response({"error": f"Invalid coordinates: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in update_location: {str(e)}", exc_info=True)
            return Response({
                "error": "Internal server error occurred during location update.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='toggle-online')
    def toggle_online(self, request):
        """
        Dedicated endpoint for drivers to switch between Online and Offline.
        Handles atomic DB state change and Redis Geospatial indexing.
        """
        try:
            profile = Profile.objects.get(user=request.user)
            
            # 1. Eligibility Check (must be a verified driver)
            if request.user.role != 'driver':
                 return Response({"error": "Only drivers can toggle online status"}, status=status.HTTP_403_FORBIDDEN)
            
            is_verified = getattr(profile, 'verification', None) and profile.verification.is_verified
            if not is_verified:
                return Response({
                    "error": "Account verification required.",
                    "detail": "Your account is not yet verified for active duty. Please complete your profile verification."
                }, status=status.HTTP_403_FORBIDDEN)

            # 2. Subscription Check
            subscription = getattr(profile, 'subscription', None)
            if not subscription or not subscription.can_go_online:
                return Response({
                    "error": "Active subscription required.",
                    "detail": "You need an active subscription to go online. Please check your plan status."
                }, status=status.HTTP_403_FORBIDDEN)

            # 3. Toggle Status
            requested_status = request.data.get('is_online')
            if requested_status is not None:
                profile.is_online = bool(requested_status)
            else:
                profile.is_online = not profile.is_online
            
            profile.last_location_update = timezone.now()
            profile.save()

            # 3. Redis Synchronization
            from flexy_backend.redis_client import redis_geo
            if profile.is_online:
                # If they have a last known location, add them to the pool immediately
                if profile.last_lat and profile.last_lng:
                    redis_geo.geo_add_driver(str(profile.pk), profile.last_lat, profile.last_lng)
            else:
                # Remove from pool when going offline using the Correct API
                redis_geo.geo_remove_driver(str(profile.pk))

            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='apply-referral')
    def apply_referral(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
        code = request.data.get('referral_code')
        if not code:
            return Response({"error": "referral_code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        if profile.referred_by:
            return Response({"error": "You have already applied a referral code."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            referrer_profile = Profile.objects.get(referral_code=code)
        except Profile.DoesNotExist:
            return Response({"error": "Invalid referral code."}, status=status.HTTP_400_BAD_REQUEST)
            
        if referrer_profile == profile:
            return Response({"error": "You cannot refer yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
        profile.referred_by = referrer_profile
        profile.save()
        
        return Response({
            "message": "Referral code applied successfully.",
            "referred_by": referrer_profile.referral_code
        }, status=status.HTTP_200_OK)
