from rest_framework import status, generics, permissions, views
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
    PasswordResetSerializer
)
from .models import DeletionRequest, OTPCode
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
        email = request.data.get("email")
        password = request.data.get("password")
        
        user = authenticate(username=email, password=password)
        if user:
            if not user.is_email_verified:
                return Response({"error": "Email not verified. Please verify your email to login."}, status=status.HTTP_403_FORBIDDEN)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })
        
        if not User.objects.filter(email=email).exists():
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
        
        email = serializer.validated_data['email']
        otp_type = serializer.validated_data['type']
        
        try:
            user = User.objects.get(email=email)
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
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        otp_type = serializer.validated_data['type']
        
        try:
            user = User.objects.get(email=email)
            otp_obj = OTPCode.objects.filter(
                user=user, 
                code=otp, 
                type=otp_type, 
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(email=email)
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

    @extend_schema(
        parameters=[
            OpenApiParameter("provider", OpenApiTypes.STR, OpenApiParameter.PATH, description="Social provider name (google, apple, etc.)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        auth=[]
    )
    def get(self, request, provider):
        # Placeholder for social callback
        return Response({"message": f"Social auth callback for {provider} received"})

class UserMeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Hard delete the user record.
        # This will cascade and delete Profile, DriverVerification, etc.
        instance.delete()
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
