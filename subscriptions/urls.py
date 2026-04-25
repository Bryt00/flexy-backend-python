from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet

router = DefaultRouter()
router.register(r'plans', SubscriptionViewSet, basename='subscription-plan')

urlpatterns = [
    path('status/', SubscriptionViewSet.as_view({'get': 'status'}), name='subscription-status'),
    path('pay/', SubscriptionViewSet.as_view({'post': 'pay'}), name='subscription-pay'),
    path('verify/', SubscriptionViewSet.as_view({'post': 'verify'}), name='subscription-verify'),
    path('', include(router.urls)),
]
