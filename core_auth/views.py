from rest_framework import status, generics, permissions, views
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
import random
from django.utils import timezone
from datetime import timedelta
from .serializers import (
    UserSerializer, RegisterSerializer, DeletionRequestSerializer,
    LoginRequestSerializer, TokenResponseSerializer, OTPRequestSerializer,
    OTPVerifySerializer, RefreshTokenRequestSerializer, RefreshTokenResponseSerializer,
    PasswordResetSerializer, SocialAuthSerializer
)
from .models import DeletionRequest, OTPCode
from integrations.social_auth_service import SocialAuthService
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """Creates a new user account and sends an OTP to verify the email address."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # Ensure invalid tokens don't block registration

    @extend_schema(
        tags=['Authentication'],
        summary='Register a new user',
        description=(
            'Creates a new user account with email, password, and role.\n\n'
            '- A 4-digit OTP is sent to the provided email for verification.\n'
            '- The account remains **inactive** until email verification via `POST /v1/auth/otp/verify/`.\n'
            '- An optional `referral_code` triggers double-sided welcome rewards (GH₵ 5.00 promo codes).\n\n'
            '**Roles:** `rider` (default), `driver`'
        ),
        responses={
            201: OpenApiResponse(
                response=inline_serializer(
                    name='RegisterResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                        'user': UserSerializer(),
                    }
                ),
                description='Registration successful. OTP sent to email.'
            ),
            400: OpenApiResponse(description='Validation error (invalid email, weak password, bad referral code).'),
        },
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate OTP for email verification
        otp_code = str(random.randint(1000, 9999))
        OTPCode.objects.create(
            user=user,
            code=otp_code,
            type='email_verification',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Send OTP Email
        from integrations.email_service import EmailService
        EmailService.send_otp_email(user.email, otp_code)
        
        return Response({
            "message": "Registration successful. Please verify your email with the OTP sent.",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)

class LoginView(views.APIView):
    """Authenticates a user with email and password, returning JWT tokens."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # Ensure invalid tokens don't block login

    @extend_schema(
        tags=['Authentication'],
        summary='Login with email and password',
        description=(
            'Authenticates a user and returns JWT access + refresh tokens.\n\n'
            '**Error Scenarios:**\n'
            '- `403 unverified_email` — Email not yet verified. A new OTP is automatically sent.\n'
            '- `401` — Invalid credentials or account not found.\n\n'
            'The `role` field is informational and does **not** grant privilege escalation on existing accounts.'
        ),
        request=LoginRequestSerializer,
        responses={
            200: TokenResponseSerializer,
            401: OpenApiResponse(description='Invalid credentials or account not found.'),
            403: OpenApiResponse(
                response=inline_serializer(
                    name='UnverifiedEmailResponse',
                    fields={
                        'error': drf_serializers.CharField(default='unverified_email'),
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='Email not verified. A new OTP has been automatically sent.'
            ),
        },
        auth=[],
    )
    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password")
        requested_role = request.data.get("role", "rider")
        
        # Robust normalization of role
        if not requested_role:
            requested_role = 'rider'
        requested_role = str(requested_role).lower().strip()
        if requested_role == 'passenger':
            requested_role = 'rider'
        if requested_role not in ['rider', 'driver', 'partner', 'admin', 'super_admin']:
            requested_role = 'rider'
        
        # Use __iexact to ensure login works regardless of email capitalization
        user = User.objects.filter(email__iexact=email).first()
        if user and user.check_password(password):
            # Ensure users with blank or invalid legacy roles default to rider
            # Do NOT trust requested_role for existing users (Privilege Escalation)
            user_updated = False
            current_role = getattr(user, 'role', None)
            if not current_role or current_role == '' or current_role == 'passenger':
                user.role = 'rider'
                user_updated = True
            if user_updated:
                user.save()
            
            if not user.is_email_verified:
                # Automatically send a new OTP
                from .models import OTPCode
                from integrations.email_service import EmailService
                
                # Rate limit check (optional but good practice)
                last_otp = OTPCode.objects.filter(user=user, type='email_verification').order_by('-created_at').first()
                if not last_otp or timezone.now() - last_otp.created_at >= timedelta(minutes=1):
                    OTPCode.objects.filter(user=user, type='email_verification', is_used=False).update(is_used=True)
                    otp_code = str(random.randint(1000, 9999))
                    OTPCode.objects.create(
                        user=user,
                        code=otp_code,
                        type='email_verification',
                        expires_at=timezone.now() + timedelta(minutes=10)
                    )
                    EmailService.send_otp_email(user.email, otp_code)
                
                return Response({
                    "error": "unverified_email",
                    "message": "Email not verified. A new OTP has been sent."
                }, status=status.HTTP_403_FORBIDDEN)
            
            update_last_login(None, user)
            if not user.session_key:
                import uuid
                user.session_key = uuid.uuid4()
                user.save(update_fields=['session_key'])
            refresh = RefreshToken.for_user(user)
            refresh['session_key'] = str(user.session_key)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })
        
        if not user:
            return Response({"error": "Account with this email was not found."}, status=status.HTTP_401_UNAUTHORIZED)
            
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class CustomTokenRefreshView(views.APIView):
    """Exchanges a refresh token for a new access + refresh token pair."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Authentication'],
        summary='Refresh JWT tokens',
        description=(
            'Exchanges a valid refresh token for a new access token and rotated refresh token.\n\n'
            'Includes session key validation — if the user logged in on another device, '
            'the old refresh token is invalidated and returns `401 Session expired`.'
        ),
        request=RefreshTokenRequestSerializer,
        responses={
            200: RefreshTokenResponseSerializer,
            400: OpenApiResponse(description='Refresh token not provided.'),
            401: OpenApiResponse(description='Invalid/expired token or session expired (logged in elsewhere).'),
        },
        auth=[],
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            
            # Validate session key
            user_id = token.get('user_id')
            token_session_key = token.get('session_key')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                if str(user.session_key) != token_session_key:
                    return Response({"error": "Session expired. You logged in on another device."}, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_401_UNAUTHORIZED)
            
            return Response({
                "token": str(token.access_token),
                "refresh_token": str(token),
            })
        except Exception as e:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

class OTPRequestView(views.APIView):
    """Sends a 4-digit OTP code to the user's email for verification or password reset."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Authentication'],
        summary='Request an OTP code',
        description=(
            'Sends a 4-digit OTP to the provided email address.\n\n'
            '**Types:**\n'
            '- `email_verification` — For new account email verification\n'
            '- `password_reset` — For forgotten password flow\n\n'
            'Rate limited to 1 request per 2 minutes per user per type. OTP expires after 10 minutes.'
        ),
        request=OTPRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='OTPSentResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                        'status': drf_serializers.CharField(default='success'),
                    }
                ),
                description='OTP sent successfully.'
            ),
            404: OpenApiResponse(description='User with this email does not exist.'),
            429: OpenApiResponse(description='Rate limited — please wait 2 minutes between requests.'),
        },
        auth=[],
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].strip()
        otp_type = serializer.validated_data['type']
        
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Rate limit: 2 minutes between requests
        last_otp = OTPCode.objects.filter(user=user, type=otp_type).order_by('-created_at').first()
        if last_otp and timezone.now() - last_otp.created_at < timedelta(minutes=2):
            return Response({"error": "Please wait 2 minutes before requesting a new code."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Invalidate old OTPs of same type
        OTPCode.objects.filter(user=user, type=otp_type, is_used=False).update(is_used=True)
        
        otp_code = str(random.randint(1000, 9999))
        OTPCode.objects.create(
            user=user,
            code=otp_code,
            type=otp_type,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        from integrations.email_service import EmailService
        EmailService.send_otp_email(email, otp_code)
        
        return Response({"message": f"OTP sent to {email}", "status": "success"})

class OTPVerifyView(views.APIView):
    """Verifies an OTP code. For email verification, activates the account and returns tokens."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Authentication'],
        summary='Verify an OTP code',
        description=(
            'Validates the 4-digit OTP sent to the user\'s email.\n\n'
            '**Behaviour by type:**\n'
            '- `email_verification` — Activates the account, sends welcome email, returns JWT tokens.\n'
            '- `password_reset` — Returns a signed `reset_token` (valid 15 minutes) for use with '
            '`POST /v1/auth/password/reset/`.\n\n'
            'OTPs are single-use and expire after 10 minutes.'
        ),
        request=OTPVerifySerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='OTPVerifyResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                        'status': drf_serializers.CharField(default='success'),
                        'user': UserSerializer(required=False),
                        'token': drf_serializers.CharField(required=False, help_text='JWT access token (email_verification only)'),
                        'refresh_token': drf_serializers.CharField(required=False, help_text='JWT refresh token (email_verification only)'),
                        'reset_token': drf_serializers.CharField(required=False, help_text='Signed reset token (password_reset only)'),
                    }
                ),
                description='OTP verified successfully.'
            ),
            400: OpenApiResponse(description='Invalid or expired OTP.'),
        },
        auth=[],
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].strip()
        otp = serializer.validated_data['otp']
        otp_type = serializer.validated_data['type']
        
        try:
            user = User.objects.get(email__iexact=email)
            otp_obj = OTPCode.objects.filter(
                user=user, 
                code=otp, 
                type=otp_type, 
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only mark as used if it's for email verification.
        # For password reset, we keep it active so PasswordResetView can verify it again during the actual reset.
        if otp_type != 'password_reset':
            otp_obj.is_used = True
            otp_obj.save()
        
        if otp_type == 'email_verification':
            user.is_email_verified = True
            user.is_active = True
            user.save()
            
            # Send Welcome Email
            from integrations.email_service import EmailService
            EmailService.send_welcome_email(user)
            
            update_last_login(None, user)
            import uuid
            user.session_key = uuid.uuid4()
            user.save(update_fields=['session_key'])
            refresh = RefreshToken.for_user(user)
            refresh['session_key'] = str(user.session_key)
            return Response({
                "message": "Email verified successfully",
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "status": "success"
            })

        if otp_type == 'password_reset':
            from django.core import signing
            reset_token = signing.dumps({'user_id': str(user.id), 'email': user.email})
            return Response({
                "message": "OTP verified successfully",
                "reset_token": reset_token,
                "status": "success"
            })
            
        return Response({"message": "OTP verified successfully", "status": "success"})

class PasswordResetView(views.APIView):
    """Resets a user's password using a verified OTP or signed reset token."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Authentication'],
        summary='Reset password',
        description=(
            'Sets a new password for the user. Requires either:\n\n'
            '1. A `reset_token` obtained from `POST /v1/auth/otp/verify/` (preferred, valid 15 min), OR\n'
            '2. A raw `otp` code (fallback)\n\n'
            'On success, all existing sessions are invalidated (session_key rotated) and a '
            'security notification email is sent.'
        ),
        request=PasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='PasswordResetResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                        'status': drf_serializers.CharField(default='success'),
                    }
                ),
                description='Password reset successfully.'
            ),
            400: OpenApiResponse(description='Invalid/expired OTP or reset token.'),
            404: OpenApiResponse(description='User with this email does not exist.'),
        },
        auth=[],
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].strip().lower()
        otp = serializer.validated_data.get('otp')
        reset_token = serializer.validated_data.get('reset_token')
        new_password = serializer.validated_data['new_password']
        
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        is_verified = False

        # 1. Verification via signed reset_token (15 minute max_age)
        if reset_token:
            from django.core import signing
            try:
                data = signing.loads(reset_token, max_age=900)
                if data.get('email', '').lower() == email or data.get('user_id') == str(user.id):
                    is_verified = True
            except Exception:
                return Response({"error": "Invalid or expired reset token. Please request a new code."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Fallback verification via OTP code
        if not is_verified and otp:
            try:
                otp_obj = OTPCode.objects.filter(
                    user=user, 
                    code=otp, 
                    type='password_reset', 
                    is_used=False,
                    expires_at__gt=timezone.now()
                ).latest('created_at')
                otp_obj.is_used = True
                otp_obj.save()
                is_verified = True
            except OTPCode.DoesNotExist:
                pass

        if not is_verified:
            return Response({"error": "Invalid or expired OTP code or reset token."}, status=status.HTTP_400_BAD_REQUEST)

        # Revoke previous sessions on all devices for security
        import uuid
        user.session_key = uuid.uuid4()
        user.set_password(new_password)
        if not user.is_email_verified:
            user.is_email_verified = True
            user.is_active = True
        user.save()

        # Invalidate old unused OTPs
        OTPCode.objects.filter(user=user, type='password_reset', is_used=False).update(is_used=True)

        # Send security notification email
        from integrations.email_service import EmailService
        EmailService.send_password_reset_success_email(user.email)

        return Response({
            "message": "Password reset successfully. Please log in with your new password.",
            "status": "success"
        }, status=status.HTTP_200_OK)

class SocialAuthView(views.APIView):
    """Authenticates or registers a user via Google or Apple OAuth tokens."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Authentication'],
        summary='Social login (Google / Apple)',
        description=(
            'Authenticates a user using a Google or Apple OAuth token.\n\n'
            '**Behaviour:**\n'
            '1. If a user with the social ID exists → returns tokens (login)\n'
            '2. If the email matches an existing account → links the social ID and returns tokens\n'
            '3. If no match → creates a new account (auto-verified) and returns tokens\n\n'
            '**Providers:** `google`, `apple`'
        ),
        request=SocialAuthSerializer,
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(description='Unsupported provider or missing email for new account.'),
            401: OpenApiResponse(description='Invalid or expired OAuth token.'),
        },
        auth=[],
    )
    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        token = serializer.validated_data['token']
        role = serializer.validated_data.get('role', 'rider')

        # Robust normalization of role
        if not role:
            role = 'rider'
        role = str(role).lower().strip()
        if role == 'passenger':
            role = 'rider'
        if role not in ['rider', 'driver', 'partner', 'admin', 'super_admin']:
            role = 'rider'

        try:
            if provider == 'google':
                user_info = SocialAuthService.verify_google_token(token)
                social_field = 'google_id'
            elif provider == 'apple':
                user_info = SocialAuthService.verify_apple_token(token)
                social_field = 'apple_id'
            else:
                return Response({"error": "Unsupported provider"}, status=status.HTTP_400_BAD_REQUEST)

            email = user_info.get('email')
            social_id = user_info.get('social_id')

            if not social_id:
                return Response({"error": "Could not retrieve social ID from provider"}, status=status.HTTP_400_BAD_REQUEST)

            # 1. Try finding user by social ID
            user = User.objects.filter(**{social_field: social_id}).first()

            if not user and email:
                # 2. Try finding user by email
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    # Link account
                    setattr(user, social_field, social_id)
                    user.is_email_verified = True
                    user.save()

            if user:
                # Ensure existing users with blank or invalid legacy roles default to rider
                # Do NOT trust role from payload for existing users (Privilege Escalation)
                user_updated = False
                current_role = getattr(user, 'role', None)
                if not current_role or current_role == '' or current_role == 'passenger':
                    user.role = 'rider'
                    user_updated = True
                if user_updated:
                    user.save()

            if not user:
                # 3. Create new user
                if not email:
                    return Response({"error": "Email is required to create a new account"}, status=status.HTTP_400_BAD_REQUEST)
                
                user = User.objects.create_user(
                    email=email,
                    role=role,
                    is_email_verified=True,
                    **{social_field: social_id}
                )
                
                # Send Welcome Email safely
                try:
                    from integrations.email_service import EmailService
                    EmailService.send_welcome_email(user)
                except Exception as email_err:
                    import logging
                    logging.getLogger(__name__).warning(f"Could not trigger welcome email: {email_err}")

            if not user.session_key:
                import uuid
                user.session_key = uuid.uuid4()
                user.save(update_fields=['session_key'])
            refresh = RefreshToken.for_user(user)
            refresh['session_key'] = str(user.session_key)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })

        except AuthenticationFailed as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Social auth unexpected error: {str(e)}", exc_info=True)
            return Response({"error": f"An error occurred during social authentication: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema_view(
    retrieve=extend_schema(
        tags=['Authentication'],
        summary='Get current user',
        description='Returns the authenticated user\'s account details (email, role, verification status).',
    ),
    update=extend_schema(
        tags=['Authentication'],
        summary='Update current user',
        description='Fully updates the authenticated user\'s account fields.',
    ),
    partial_update=extend_schema(
        tags=['Authentication'],
        summary='Partially update current user',
        description='Partially updates the authenticated user\'s account fields.',
    ),
    destroy=extend_schema(
        tags=['Authentication'],
        summary='Deactivate current user',
        description='Soft-deletes the user account by setting `is_active=False`. Preserves data for accounting.',
    ),
)
class UserMeView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieves, updates, or deactivates the currently authenticated user's account."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Soft delete the user record to preserve history and accounting.
        instance.is_active = False
        instance.save()

class LogoutView(views.APIView):
    """Blacklists the refresh token, effectively logging the user out."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='Logout',
        description=(
            'Blacklists the provided refresh token to invalidate the session.\n\n'
            'Even if blacklisting fails (e.g. token already expired), returns success — '
            'the client should discard tokens regardless.'
        ),
        request=RefreshTokenRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='LogoutResponse',
                    fields={
                        'message': drf_serializers.CharField(default='Successfully logged out'),
                        'status': drf_serializers.CharField(default='success'),
                    }
                ),
                description='Successfully logged out.'
            ),
        },
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Successfully logged out", "status": "success"}, status=status.HTTP_200_OK)
        except Exception:
            # If blacklisting fails (e.g. token already expired), still return success as user wants to logout
            return Response({"message": "Successfully logged out", "status": "success"}, status=status.HTTP_200_OK)

class ChangePasswordView(views.APIView):
    """Changes the authenticated user's password after verifying the current one."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='Change password',
        description=(
            'Changes the authenticated user\'s password.\n\n'
            'Requires the current password for verification. On success:\n'
            '- All existing sessions are invalidated (session_key rotated)\n'
            '- A security notification email is sent\n\n'
            'The new password must pass Django\'s password validation rules.'
        ),
        request=inline_serializer(
            name='ChangePasswordRequest',
            fields={
                'current_password': drf_serializers.CharField(help_text='The user\'s current password.'),
                'new_password': drf_serializers.CharField(help_text='The desired new password.'),
            }
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='ChangePasswordResponse',
                    fields={
                        'message': drf_serializers.CharField(default='Password updated successfully'),
                        'status': drf_serializers.CharField(default='success'),
                    }
                ),
                description='Password changed successfully.'
            ),
            400: OpenApiResponse(description='Missing fields, incorrect current password, or weak new password.'),
        },
    )
    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"error": "Both current_password and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)

        # Run Django password validation
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({"error": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        import uuid
        user.session_key = uuid.uuid4()
        user.set_password(new_password)
        user.save()

        # Send security notification email
        from integrations.email_service import EmailService
        EmailService.send_password_reset_success_email(user.email)
        
        return Response({"message": "Password updated successfully", "status": "success"}, status=status.HTTP_200_OK)
