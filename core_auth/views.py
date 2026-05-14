from rest_framework import status, generics, permissions, views
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # Ensure invalid tokens don't block registration

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
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] # Ensure invalid tokens don't block login

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: TokenResponseSerializer},
        auth=[]
    )
    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password")
        
        # Use __iexact to ensure login works regardless of email capitalization
        user = User.objects.filter(email__iexact=email).first()
        if user and user.check_password(password):
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
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })
        
        if not user:
            return Response({"error": "Account with this email was not found."}, status=status.HTTP_401_UNAUTHORIZED)
            
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class CustomTokenRefreshView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=RefreshTokenRequestSerializer,
        responses={200: RefreshTokenResponseSerializer},
        auth=[]
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            return Response({
                "token": str(token.access_token),
                "refresh_token": str(token),
            })
        except Exception as e:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

class OTPRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=OTPRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
        auth=[]
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
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=OTPVerifySerializer,
        responses={200: OpenApiTypes.OBJECT},
        auth=[]
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
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Email verified successfully",
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "status": "success"
            })
            
        return Response({"message": "OTP verified successfully", "status": "success"})

class PasswordResetView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=PasswordResetSerializer,
        responses={200: OpenApiTypes.OBJECT},
        auth=[]
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].strip()
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(email__iexact=email)
            otp_obj = OTPCode.objects.filter(
                user=user, 
                code=otp, 
                type='password_reset', 
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_obj.is_used = True
        otp_obj.save()
        
        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Password reset successfully", "status": "success"})

class SocialAuthView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=SocialAuthSerializer,
        responses={200: TokenResponseSerializer},
        auth=[]
    )
    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        token = serializer.validated_data['token']
        role = serializer.validated_data.get('role', 'rider')

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
                
                # Send Welcome Email
                from integrations.email_service import EmailService
                EmailService.send_welcome_email(user)

            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })

        except AuthenticationFailed as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": "An error occurred during social authentication"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserMeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Soft delete the user record to preserve history and accounting.
        instance.is_active = False
        instance.save()
class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=RefreshTokenRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
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
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"error": "Both current_password and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Password updated successfully", "status": "success"}, status=status.HTTP_200_OK)
