from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SiteSettingViewSet

router = DefaultRouter()
router.register(r'site-settings', SiteSettingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
