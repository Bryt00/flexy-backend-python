from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APIKeyViewSet, list_available_scopes

router = DefaultRouter()
router.register(r'keys', APIKeyViewSet, basename='api-key')

urlpatterns = [
    path('scopes/', list_available_scopes, name='integrations-scopes'),
    path('', include(router.urls)),
]
