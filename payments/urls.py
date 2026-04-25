from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = [
    path('wallet/', PaymentViewSet.as_view({'get': 'wallet'}), name='payment_wallet'),
    path('transactions/', PaymentViewSet.as_view({'get': 'transactions'}), name='payment_transactions'),
    path('initiate/', PaymentViewSet.as_view({'post': 'initiate'}), name='payment_initiate'),
    path('verify/<str:reference>/', PaymentViewSet.as_view({'get': 'verify'}), name='payment_verify'),
    path('webhooks/paystack/', PaymentViewSet.as_view({'post': 'webhook'}), name='payment_webhook'),
    path('', include(router.urls)),
]
