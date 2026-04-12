from django.urls import path
from .views import (
    RegisterView, LoginView, OTPRequestView, OTPVerifyView, 
    SocialAuthView, UserMeView, CustomTokenRefreshView
)

urlpatterns = [
    # Auth Routes (matching Go /auth group)
    path('register', RegisterView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('refresh', CustomTokenRefreshView.as_view(), name='token_refresh_custom'),
    path('google/callback', SocialAuthView.as_view(), {'provider': 'google'}, name='google_callback'),
    path('apple/login', SocialAuthView.as_view(), {'provider': 'apple'}, name='apple_login'),
    path('phone/otp', OTPRequestView.as_view(), name='phone_otp'),
    path('phone/verify', OTPVerifyView.as_view(), name='phone_verify'),
    
    # API Routes (matching Go /api group)
    path('api/me', UserMeView.as_view(), name='user_me'),
]
