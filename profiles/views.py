from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Profile, DriverVerification
from .serializers import ProfileSerializer, DriverVerificationSerializer
from drf_spectacular.utils import extend_schema, OpenApiTypes
from django.utils import timezone
from integrations.email_service import EmailService
from core_auth.cache_utils import cached_api_response, invalidate_user_cache

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
            def fetch_profile():
                try:
                    profile = Profile.objects.get(user=request.user)
                    serializer = self.get_serializer(profile)
                    return Response(serializer.data)
                except Profile.DoesNotExist:
                    return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            return cached_api_response(request, 'profile', timeout=300, fetcher=fetch_profile)
        
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Invalidate profile cache on mutation
        invalidate_user_cache(request.user.id, 'profile')
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
        def fetch_verification():
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            verification, created = DriverVerification.objects.get_or_create(driver=profile)
            serializer = DriverVerificationSerializer(verification)
            return Response(serializer.data)
        return cached_api_response(request, 'verification', timeout=300, fetcher=fetch_verification)
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='verification/initiate')
    def initiate_verification(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
        verification, created = DriverVerification.objects.get_or_create(driver=profile)

        # --- Re-submission Guard ---
        # Prevent tampering once verified.
        # Allow re-submission if status is PENDING, SUBMITTED (to fix mistakes), or REJECTED.
        if not created and verification.status == 'VERIFIED':
            from .serializers import DriverVerificationSerializer
            serializer = DriverVerificationSerializer(verification)
            can_update = False
            
            # If they are trying to update a specific document and it's allowed
            if request.data.get('license_url') and serializer.data.get('can_resubmit_license'):
                can_update = True
            if request.data.get('id_card_url') and serializer.data.get('can_resubmit_id_card'):
                can_update = True
            if request.data.get('insurance_url') and serializer.data.get('can_resubmit_insurance'):
                can_update = True
            if request.data.get('roadworthy_url') and serializer.data.get('can_resubmit_roadworthy'):
                can_update = True
                
            if not can_update:
                return Response({
                    'error': 'Verification already approved.',
                    'detail': 'Your account is already verified. You can only update documents that are nearing expiry.',
                    'verification_status': verification.status,
                }, status=status.HTTP_400_BAD_REQUEST)

        # Mapping frontend keys to backend fields
        license_url = request.data.get('license_url', verification.license_url)
        license_expiry_date = request.data.get('license_expiry_date', verification.license_expiry_date)
        id_card_url = request.data.get('id_card_url', verification.id_card_url)
        id_card_expiry_date = request.data.get('id_card_expiry_date', verification.id_card_expiry_date)
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
        verification.license_expiry_date = license_expiry_date
        verification.id_card_url = id_card_url
        verification.id_card_expiry_date = id_card_expiry_date
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
        def fetch_tiers():
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
        return cached_api_response(request, 'tier_definitions', timeout=900, fetcher=fetch_tiers, global_cache=True)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='location')
    def update_location(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            lat = request.data.get('lat')
            lng = request.data.get('lng')
            
            if lat is None or lng is None:
                return Response({"error": "lat and lng are required"}, status=status.HTTP_400_BAD_REQUEST)
                
            from .services.tracking_service import TrackingService
            TrackingService.update_driver_location(str(profile.pk), float(lat), float(lng))
            
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
            if not is_verified and not settings.DEBUG:
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

            # 3. Toggle Status via Centralized Service
            requested_status = request.data.get('is_online')
            is_online = bool(requested_status) if requested_status is not None else not profile.is_online
            
            from .services.tracking_service import TrackingService
            TrackingService.set_driver_online_status(str(profile.pk), is_online)
            
            # Refresh to reflect updated status in response
            profile.refresh_from_db()

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
        
        # --- DOUBLE-SIDED REWARDS & NOTIFICATIONS ---
        # 1. Instantly generate a WELCOME promo code for the referee
        import random
        from rides.models import PromoCode
        from django.utils import timezone
        from datetime import timedelta
        from notification.utils import send_notification

        try:
            welcome_code_str = f"WELCOME-{referrer_profile.referral_code}-{random.randint(100, 999)}"
            PromoCode.objects.create(
                user=profile.user,
                code=welcome_code_str,
                type='fixed',
                value=5.0,
                usage_limit=1,
                expires_at=timezone.now() + timedelta(days=30),
                active=True
            )
            
            send_notification(
                profile.user,
                title="Welcome Bonus! 🎁",
                body=f"Enjoy GH₵ 5.00 off your first ride with promo code {welcome_code_str}.",
                type='PUSH'
            )
        except Exception:
            pass

        # 2. Notify the Referrer that their friend joined
        try:
            friend_display_name = profile.full_name or profile.user.email
            send_notification(
                referrer_profile.user,
                title="Friend Joined! 👥",
                body=f"Your friend {friend_display_name} just linked your referral code! You will get GH₵ 5.00 off once they complete their first ride.",
                type='PUSH'
            )
        except Exception:
            pass
        
        return Response({
            "message": "Referral code applied successfully.",
            "referred_by": referrer_profile.referral_code
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'post'], url_path='settings/(?P<key>[^/.]+)')
    def config_settings(self, request, key=None):
        if not request.user.is_staff and not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
            
        from website.models import LegalDocument
        from core_settings.models import SiteSetting
        
        if key in ['terms_and_conditions', 'privacy_policy', 'about_us']:
            if key == 'terms_and_conditions':
                doc_type = 'terms'
            elif key == 'privacy_policy':
                doc_type = 'privacy'
            else:
                doc_type = 'about'

            if request.method == 'GET':
                doc = LegalDocument.objects.filter(document_type=doc_type).order_by('-last_updated').first()
                return Response({"value": doc.content if doc else ""})
            else:
                content = request.data.get('value', '')
                doc = LegalDocument.objects.filter(document_type=doc_type).order_by('-last_updated').first()
                if doc:
                    doc.content = content
                    doc.save()
                else:
                    if doc_type == 'terms':
                        title = 'Terms of Service'
                    elif doc_type == 'privacy':
                        title = 'Privacy Policy'
                    else:
                        title = 'About Us'
                        
                    LegalDocument.objects.create(
                        title=title,
                        slug=doc_type,
                        document_type=doc_type,
                        content=content,
                    )
                return Response({"status": "success", "value": content})
        else:
            if request.method == 'GET':
                setting = SiteSetting.objects.filter(key=key).first()
                return Response({"value": setting.value if setting else ""})
            else:
                value = request.data.get('value', '')
                setting, created = SiteSetting.objects.get_or_create(key=key, defaults={'value': value, 'name': key.replace('_', ' ').title()})
                if not created:
                    setting.value = value
                    setting.save()
                return Response({"status": "success", "value": value})
