from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SiteSettingViewSet, DeliveryCategoryViewSet, DeliveryWeightTierViewSet, DeliveryVehicleTypeViewSet, VehicleCategoryViewSet, ServiceAreaViewSet

router = DefaultRouter()
router.register(r'site-settings', SiteSettingViewSet, basename='site-settings')
router.register(r'delivery-categories', DeliveryCategoryViewSet, basename='delivery-categories')
router.register(r'delivery-weight-tiers', DeliveryWeightTierViewSet, basename='delivery-weight-tiers')
router.register(r'delivery-vehicle-types', DeliveryVehicleTypeViewSet, basename='delivery-vehicle-types')
router.register(r'vehicle-categories', VehicleCategoryViewSet, basename='vehicle-categories')
router.register(r'service-areas', ServiceAreaViewSet, basename='service-areas')


urlpatterns = [
    path('', include(router.urls)),
]
