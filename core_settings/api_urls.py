from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SiteSettingViewSet, DeliveryCategoryViewSet, DeliveryWeightTierViewSet, DeliveryVehicleTypeViewSet

router = DefaultRouter()
router.register(r'site-settings', SiteSettingViewSet, basename='site-settings')
router.register(r'delivery-categories', DeliveryCategoryViewSet, basename='delivery-categories')
router.register(r'delivery-weight-tiers', DeliveryWeightTierViewSet, basename='delivery-weight-tiers')
router.register(r'delivery-vehicle-types', DeliveryVehicleTypeViewSet, basename='delivery-vehicle-types')

urlpatterns = [
    path('', include(router.urls)),
]
