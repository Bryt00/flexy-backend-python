from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, RegisterFCMTokenView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('fcm-token/', RegisterFCMTokenView.as_view(), name='register_fcm_token'),
    path('', include(router.urls)),
]
