from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserSerializer, RegisterSerializer, DeletionRequestSerializer
from .models import DeletionRequest

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }, status=status.HTTP_201_CREATED)

class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            })
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class CustomTokenRefreshView(views.APIView):
    permission_classes = [permissions.AllowAny]

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
    def post(self, request):
        phone = request.data.get("phone")
        # Placeholder for SMS logic
        return Response({"message": f"OTP sent to {phone}", "status": "success"})

class OTPVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        phone = request.data.get("phone")
        otp = request.data.get("otp")
        # Placeholder for verification logic
        return Response({"message": "Phone verified successfully", "status": "success"})

class SocialAuthView(views.APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, provider):
        # Placeholder for social callback
        return Response({"message": f"Social auth callback for {provider} received"})

class UserMeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Create deletion request instead of immediate delete as per Go logic
        DeletionRequest.objects.get_or_create(
            user=instance,
            status='PENDING'
        )
        instance.is_active = False # Deactivate
        instance.save()
