from django.urls import path
from .views import (
    RegisterView, LoginView, OTPRequestView, OTPVerifyView, 
    SocialAuthView, UserMeView, CustomTokenRefreshView, LogoutView,
    PasswordResetView, ChangePasswordView
)

urlpatterns = [
    # Auth Routes (matching Go /auth group)
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh_custom'),
    path('otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),
    path('password/reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password/change/', ChangePasswordView.as_view(), name='password_change'),
    
    path('social/', SocialAuthView.as_view(), name='social_auth_generic'),
    path('google/callback/', SocialAuthView.as_view(), {'provider': 'google'}, name='google_callback'),
    path('apple/login/', SocialAuthView.as_view(), {'provider': 'apple'}, name='apple_login'),
    
    # API Routes (matching Go /api group)
    path('api/me/', UserMeView.as_view(), name='user_me_api'),
    path('me/', UserMeView.as_view(), name='user_me_direct'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
