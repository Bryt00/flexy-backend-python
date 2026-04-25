from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, PromoCodeViewSet

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'promos', PromoCodeViewSet, basename='promo')

urlpatterns = [
    path('', include(router.urls)),
]
