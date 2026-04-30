from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, PromoCodeViewSet, ReferralStatsView

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'promos', PromoCodeViewSet, basename='promo')

urlpatterns = [
    path('referral/stats/', ReferralStatsView.as_view(), name='referral_stats'),
    path('', include(router.urls)),
]
