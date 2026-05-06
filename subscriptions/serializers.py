from rest_framework import serializers
from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'category', 'price', 'duration_days', 'features', 'is_active']

class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = ['id', 'amount', 'paystack_reference', 'status', 'payment_date', 'created_at']

class DriverSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_active = serializers.BooleanField(source='is_currently_active', read_only=True)
    
    class Meta:
        model = DriverSubscription
        fields = [
            'id', 'plan', 'plan_details', 'status', 'expiry_date', 
            'is_active', 'auto_renew', 'trial_end_date', 'is_in_trial', 
            'trial_days_remaining'
        ]
        read_only_fields = ['status', 'expiry_date', 'trial_end_date']
