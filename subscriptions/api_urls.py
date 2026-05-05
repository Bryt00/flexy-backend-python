from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import AdminSubscriptionPlanViewSet, AdminDriverSubscriptionViewSet, AdminSubscriptionPaymentViewSet

router = DefaultRouter()
router.register(r'plans', AdminSubscriptionPlanViewSet, basename='admin-subscription-plan')
router.register(r'drivers', AdminDriverSubscriptionViewSet, basename='admin-driver-subscription')
router.register(r'payments', AdminSubscriptionPaymentViewSet, basename='admin-subscription-payment')

urlpatterns = [
    path('', include(router.urls)),
]
