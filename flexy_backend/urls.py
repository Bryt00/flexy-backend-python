from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('', include('website.urls')),
    path('advertise/', include('advertising.website_urls')),
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Versioned API Services (Mobile App Parity)
    path('v1/auth/', include('core_auth.urls')),
    path('v1/rides/', include('rides.urls')),
    path('v1/vehicles/', include('vehicles.urls')),
    path('v1/profile/', include('profiles.urls')),
    path('v1/subscriptions/', include('subscriptions.urls')),
    path('v1/notifications/', include('notification.urls')),
    path('v1/payments/', include('payments.urls')),
    path('v1/files/', include('file_manager.urls')),
    path('v1/deliveries/', include('courier.urls')),
    path('v1/integrations/', include('integrations.urls')),
    path('v1/ads/', include('advertising.urls')),
    path('v1/website/', include('website.api_urls')),
    path('v1/settings/', include('core_settings.api_urls')),
    path('v1/admin/subscriptions/', include('subscriptions.api_urls')),
    path('', include('marketing.urls')), # To match /campaigns/active
    
    # Generic API Auth (Standard DRF)
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ckeditor5/', include('django_ckeditor_5.urls'), name='ck_editor_5_upload'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
