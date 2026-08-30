from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Profile, DriverVerification
from .serializers import ProfileSerializer, DriverVerificationSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes, OpenApiResponse, inline_serializer, OpenApiParameter
from rest_framework import serializers as drf_serializers
from django.utils import timezone
from integrations.email_service import EmailService
from core_auth.cache_utils import cached_api_response, invalidate_user_cache


@extend_schema_view(
    list=extend_schema(tags=['Profiles'], summary='List all profiles', description='Admin-only. Returns all user profiles.'),
    retrieve=extend_schema(tags=['Profiles'], summary='Retrieve a profile', description='Returns a specific user profile by ID.'),
    create=extend_schema(tags=['Profiles'], summary='Create a profile', description='Creates a new user profile. Typically done automatically on registration.'),
    update=extend_schema(tags=['Profiles'], summary='Update a profile', description='Fully updates a user profile.'),
    partial_update=extend_schema(tags=['Profiles'], summary='Partially update a profile', description='Partially updates a user profile.'),
    destroy=extend_schema(tags=['Profiles'], summary='Delete a profile', description='Deletes a user profile.'),
)
class ProfileViewSet(viewsets.ModelViewSet):
    """User profile management for riders and drivers."""
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

    @extend_schema(
        tags=['Profiles'],
        summary='Get or update my profile',
        description=(
            'Multi-method endpoint for the authenticated user\'s profile.\n\n'
            '- **GET** — Returns the full profile with verification status, subscription status, and computed fields.\n'
            '- **POST/PUT/PATCH** — Creates or updates the profile (partial updates supported).\n\n'
            'Response is cached for 5 minutes on GET; cache is invalidated on mutations.'
        ),
        responses={200: ProfileSerializer},
    )
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

    @extend_schema(
        tags=['Profiles'],
        summary='Update notification preferences',
        description=(
            'Updates the authenticated user\'s notification and security preferences.\n\n'
            '**Supported fields:**\n'
            '- `notification_preferences` (object) — Push notification settings\n'
            '- `is_2fa_enabled` (boolean) — Two-factor authentication toggle\n'
            '- `is_biometric_enabled` (boolean) — Biometric login toggle'
        ),
        request=inline_serializer(
            name='PreferencesRequest',
            fields={
                'notification_preferences': drf_serializers.JSONField(required=False, help_text='Push notification settings object.'),
                'is_2fa_enabled': drf_serializers.BooleanField(required=False),
                'is_biometric_enabled': drf_serializers.BooleanField(required=False),
            }
        ),
        responses={200: ProfileSerializer},
    )
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
        if 'is_biometric_enabled' in request.data:
            profile.is_biometric_enabled = request.data['is_biometric_enabled']
            
        profile.save()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @extend_schema(
        tags=['Profiles'],
        summary='Get driver verification status',
        description=(
            'Returns the driver\'s verification status and document details.\n\n'
            'Includes computed `can_resubmit_*` flags indicating which documents are '
            'nearing expiry and can be re-uploaded.'
        ),
        responses={200: DriverVerificationSerializer},
    )
    @action(detail=False, methods=['get'], url_path='verification')
    def verification_status(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        verification, created = DriverVerification.objects.get_or_create(driver=profile)
        serializer = DriverVerificationSerializer(verification)
        return Response(serializer.data)

    @extend_schema(
        tags=['Profiles'],
        summary='Submit driver verification documents',
        description=(
            'Submits or updates driver verification documents for admin review.\n\n'
            '**Required documents (PDF only):**\n'
            '- `license_url` — Driver\'s license\n'
            '- `id_card_url` — National ID card\n'
            '- `insurance_url` — Vehicle insurance\n'
            '- `roadworthy_url` — Roadworthy certificate\n'
            '- `vehicle_video_url` — Vehicle inspection video (any format)\n\n'
            '**Re-submission rules:**\n'
            '- Verified drivers can only update documents nearing expiry\n'
            '- PENDING/SUBMITTED/REJECTED drivers can freely re-submit\n\n'
            'Triggers an admin email notification on submission.'
        ),
        request=inline_serializer(
            name='VerificationSubmitRequest',
            fields={
                'license_number': drf_serializers.CharField(required=False),
                'license_url': drf_serializers.URLField(required=False, help_text='URL to uploaded PDF.'),
                'license_expiry_date': drf_serializers.DateField(required=False),
                'id_card_url': drf_serializers.URLField(required=False, help_text='URL to uploaded PDF.'),
                'id_card_expiry_date': drf_serializers.DateField(required=False),
                'insurance_url': drf_serializers.URLField(required=False, help_text='URL to uploaded PDF.'),
                'roadworthy_url': drf_serializers.URLField(required=False, help_text='URL to uploaded PDF.'),
                'vehicle_video_url': drf_serializers.URLField(required=False, help_text='URL to uploaded video.'),
            }
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='VerificationSubmitResponse',
                    fields={
                        'status': drf_serializers.CharField(),
                        'profile_id': drf_serializers.UUIDField(),
                        'verification_status': drf_serializers.CharField(),
                    }
                ),
                description='Verification documents submitted for review.'
            ),
            400: OpenApiResponse(description='Already verified (no resubmit allowed) or invalid file format.'),
        },
    )
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
        license_number = request.data.get('license_number', request.data.get('license_plate', verification.license_number))
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

        if license_number:
            verification.license_number = license_number
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

    @extend_schema(
        tags=['Profiles'],
        summary='Get driver tier definitions',
        description=(
            'Returns the available driver loyalty tiers and their point thresholds.\n\n'
            '**Tiers:** Silver (0+), Gold (500+), Platinum (1500+)\n\n'
            'Response is cached globally for 15 minutes.'
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='TierDefinition',
                    many=True,
                    fields={
                        'name': drf_serializers.CharField(),
                        'min_points': drf_serializers.IntegerField(),
                        'description': drf_serializers.CharField(),
                        'benefits': drf_serializers.ListField(child=drf_serializers.CharField()),
                    }
                ),
                description='List of tier definitions.'
            ),
        },
    )
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

    @extend_schema(
        tags=['Profiles'],
        summary='Update driver GPS location',
        description=(
            'Updates the authenticated driver\'s real-time GPS coordinates in Redis.\n\n'
            'Called frequently by the driver app while online. Used for:\n'
            '- Ride matching (nearest driver selection)\n'
            '- Nearby vehicles map display\n'
            '- Surge pricing calculations'
        ),
        request=inline_serializer(
            name='LocationUpdateRequest',
            fields={
                'lat': drf_serializers.FloatField(help_text='Latitude (-90 to 90).'),
                'lng': drf_serializers.FloatField(help_text='Longitude (-180 to 180).'),
            }
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='LocationUpdateResponse',
                    fields={'status': drf_serializers.CharField(default='Location updated')},
                ),
                description='Location updated in Redis geospatial index.'
            ),
            400: OpenApiResponse(description='Missing or invalid coordinates.'),
            404: OpenApiResponse(description='Profile not found.'),
        },
    )
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

    @extend_schema(
        tags=['Profiles'],
        summary='Toggle driver online/offline status',
        description=(
            'Switches a driver between Online and Offline mode.\n\n'
            '**Going online requires:**\n'
            '1. User role must be `driver`\n'
            '2. Account must be **verified** (all documents approved)\n'
            '3. Must have an **active subscription** (or be in free trial)\n\n'
            'Going offline has no restrictions. Updates Redis geospatial index and DB atomically.'
        ),
        request=inline_serializer(
            name='ToggleOnlineRequest',
            fields={
                'is_online': drf_serializers.BooleanField(
                    required=False,
                    help_text='Explicit online state. If omitted, toggles the current state.'
                ),
            }
        ),
        responses={
            200: ProfileSerializer,
            403: OpenApiResponse(description='Not a driver, not verified, or no active subscription.'),
            404: OpenApiResponse(description='Profile not found.'),
        },
    )
    @action(detail=False, methods=['post'], url_path='toggle-online')
    def toggle_online(self, request):
        """
        Dedicated endpoint for drivers to switch between Online and Offline.
        Handles atomic DB state change and Redis Geospatial indexing.
        """
        try:
            profile = Profile.objects.get(user=request.user)
            
            # 1. Base Eligibility
            if request.user.role != 'driver':
                 return Response({"error": "Only drivers can toggle online status"}, status=status.HTTP_403_FORBIDDEN)
            
            requested_status = request.data.get('is_online')
            is_online = bool(requested_status) if requested_status is not None else not profile.is_online

            # Only enforce restrictions if the driver is attempting to go ONLINE
            if is_online:
                # 2. Verification Check
                verification = profile.verification if hasattr(profile, 'verification') else None
                is_verified = verification and verification.is_verified
                if not is_verified:
                    return Response({
                        "error": "Account verification required.",
                        "detail": "Your account is not yet verified for active duty. Please complete your profile verification."
                    }, status=status.HTTP_403_FORBIDDEN)

                # 3. Subscription Check
                subscription = profile.subscription if hasattr(profile, 'subscription') else None
                
                if not subscription or not subscription.can_go_online:
                    if subscription and subscription.is_trial_used and not subscription.is_in_trial and subscription.status != 'active':
                        return Response({
                            "error": "Free trial expired.",
                            "detail": "Your 14-day free trial has expired. Please purchase a subscription plan to go online and continue driving."
                        }, status=status.HTTP_403_FORBIDDEN)
                    else:
                        return Response({
                            "error": "Active subscription required.",
                            "detail": "You need an active subscription to go online. Please check your plan status."
                        }, status=status.HTTP_403_FORBIDDEN)

            # 4. Toggle Status via Centralized Service
            from .services.tracking_service import TrackingService
            TrackingService.set_driver_online_status(str(profile.pk), is_online)
            
            # Invalidate profile cache so subsequent GET /me calls reflect the new status
            from core_auth.cache_utils import invalidate_user_cache
            invalidate_user_cache(request.user.id, 'profile')
            
            # Refresh to reflect updated status in response
            profile.refresh_from_db()

            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=['Profiles'],
        summary='Apply a referral code',
        description=(
            'Links a referral code to the authenticated user\'s profile.\n\n'
            '**Rewards (immediate):**\n'
            '- Referee gets a GH₵ 5.00 WELCOME promo code (valid 30 days)\n'
            '- Referrer is notified via push that their friend joined\n\n'
            'Can only be applied once per user. Self-referral is blocked.'
        ),
        request=inline_serializer(
            name='ApplyReferralRequest',
            fields={
                'referral_code': drf_serializers.CharField(help_text='The referrer\'s unique referral code.'),
            }
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='ApplyReferralResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                        'referred_by': drf_serializers.CharField(),
                    }
                ),
                description='Referral code applied successfully.'
            ),
            400: OpenApiResponse(description='Invalid code, already applied, or self-referral attempt.'),
        },
    )
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
                title="Welcome Bonus!",
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
                title="Friend Joined!",
                body=f"Your friend {friend_display_name} just linked your referral code! You will get GH₵ 5.00 off once they complete their first ride.",
                type='PUSH'
            )
        except Exception:
            pass
        
        return Response({
            "message": "Referral code applied successfully.",
            "referred_by": referrer_profile.referral_code
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Settings'],
        summary='Get or set a platform setting',
        description=(
            'Admin-only endpoint to read/write platform configuration values.\n\n'
            '**Special keys:** `terms_and_conditions`, `privacy_policy`, `about_us` '
            '(stored as LegalDocument records). All other keys use the SiteSetting model.'
        ),
        parameters=[
            OpenApiParameter(name='key', type=str, location='path', required=True, description='Setting key (terms_and_conditions, privacy_policy, about_us, etc.).'),
        ],
        responses={200: OpenApiResponse(description='Setting value.')},
    )
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
