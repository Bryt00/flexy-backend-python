from rest_framework import viewsets, permissions
from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment
from .serializers import SubscriptionPlanSerializer, DriverSubscriptionSerializer, SubscriptionPaymentSerializer

class AdminSubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all().order_by('-created_at')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminDriverSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = DriverSubscription.objects.all().order_by('-created_at')
    serializer_class = DriverSubscriptionSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminSubscriptionPaymentViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPayment.objects.all().order_by('-created_at')
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAdminUser]
