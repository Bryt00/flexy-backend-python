from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('me', NotificationViewSet.as_view({'get': 'me'}), name='notifications_me'),
    path('read/all', NotificationViewSet.as_view({'post': 'read_all'}), name='notifications_read_all'),
    path('read/<uuid:pk>', NotificationViewSet.as_view({'post': 'read'}), name='notifications_read'),
    path('', include(router.urls)),
]
