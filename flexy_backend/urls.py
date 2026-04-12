from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .tests_monitoring import debug_sentry

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/debug-sentry/', debug_sentry, name='debug_sentry'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Versioned API Services (Mobile App Parity)
    path('v1/auth/', include('core_auth.urls')),
    path('v1/rides/', include('rides.urls')),
    path('v1/api/', include('core_auth.urls')),
    path('v1/profile/', include('profiles.urls')),
    path('v1/notifications/', include('notification.urls')),
    path('v1/payments/', include('payments.urls')),
    
    # Generic API Auth (Standard DRF)
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
