from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', ProfileViewSet)

urlpatterns = [
    path('me', ProfileViewSet.as_view({'get': 'me', 'post': 'me', 'put': 'me'}), name='profile_me'),
    path('verification/<uuid:pk>', ProfileViewSet.as_view({'get': 'verification_status'}), name='verification_status'),
    path('', include(router.urls)),
]
