from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from .models import SubscriptionPlan, DriverSubscription, SubscriptionPayment
from .serializers import SubscriptionPlanSerializer, DriverSubscriptionSerializer, SubscriptionPaymentSerializer
from .services import PaystackService

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SubscriptionPlan.objects.filter(is_active=True)

        if hasattr(user, 'profile') and hasattr(user.profile, 'verification'):
            category = user.profile.verification.assigned_category
            if category and category != 'none':
                return qs.filter(category=category)

        # Drivers only see plans after verification and category assignment
        return qs.none()

    @action(detail=False, methods=['get'])
    def status(self, request):
        if not hasattr(request.user, 'profile'):
            return Response({"error": "User has no profile"}, status=status.HTTP_400_BAD_REQUEST)
        
        subscription, created = DriverSubscription.objects.get_or_create(profile=request.user.profile)
        serializer = DriverSubscriptionSerializer(subscription)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def pay(self, request):
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({"error": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except (SubscriptionPlan.DoesNotExist, ValueError):
            return Response({"error": "Invalid or inactive plan"}, status=status.HTTP_404_NOT_FOUND)

        profile = request.user.profile
        
        # Initialize Paystack transaction
        service = PaystackService()
        metadata = {
            "driver_id": str(profile.user_id),
            "plan_id": str(plan.id),
            "type": "subscription"
        }
        
        response = service.initialize_transaction(
            email=request.user.email,
            amount=plan.price,
            metadata=metadata,
            callback_url="https://flexyride.com/payment-callback"
        )
        
        if response.get('status'):
            data = response.get('data')
            reference = data.get('reference')
            
            # Create a pending payment record
            subscription, _ = DriverSubscription.objects.get_or_create(profile=profile)
            SubscriptionPayment.objects.create(
                subscription=subscription,
                plan=plan,
                amount=plan.price,
                paystack_reference=reference,
                status='pending'
            )
            
            return Response({
                "checkout_url": data.get('authorization_url'),
                "access_code": data.get('access_code'),
                "reference": reference,
                "amount": int(float(plan.price) * 100),
                "status": "success"
            })
        
        return Response({
            "error": "Could not initialize payment",
            "message": response.get('message')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        reference = request.data.get('reference')
        if not reference:
            return Response({"error": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            payment = SubscriptionPayment.objects.get(paystack_reference=reference)
        except SubscriptionPayment.DoesNotExist:
            return Response({"error": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if payment.status == 'success':
            return Response({
                "message": "Payment already verified", 
                "status": "success",
                "expiry_date": payment.subscription.expiry_date
            })

        # Verify with Paystack
        service = PaystackService()
        response = service.verify_transaction(reference)
        
        if response.get('status') and response.get('data', {}).get('status') == 'success':
            with transaction.atomic():
                # Update payment record
                payment.status = 'success'
                payment.payment_date = timezone.now()
                payment.save()
                
                # Activate/Update subscription
                subscription = payment.subscription
                subscription.plan = payment.plan
                
                # Calculate new expiry date
                # If currently active, extend from expiry, else from now
                start_from = timezone.now()
                if subscription.is_currently_active and subscription.expiry_date:
                    start_from = subscription.expiry_date
                
                if not subscription.start_date:
                    subscription.start_date = timezone.now()
                
                subscription.expiry_date = start_from + timedelta(days=payment.plan.duration_days)
                subscription.status = 'active'
                subscription.save()
                
            return Response({
                "message": "Subscription activated successfully",
                "expiry_date": subscription.expiry_date,
                "status": "success"
            })
            
        return Response({
            "error": "Payment verification failed",
            "message": response.get('message', 'Transaction was not successful')
        }, status=status.HTTP_400_BAD_REQUEST)
