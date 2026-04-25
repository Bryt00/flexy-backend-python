from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer
from integrations.paystack import PaystackService

from drf_spectacular.utils import extend_schema, OpenApiTypes

class PaymentViewSet(viewsets.GenericViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def wallet(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        txs = wallet.transactions.all().order_by('-created_at')
        serializer = TransactionSerializer(txs, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def earnings(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({
            "balance": float(wallet.balance),
            "currency": wallet.currency,
            "total_rides": 0,
            "deliveries": 0,
            "tips": 0.0,
            "points": 0
        })

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.db.models import Sum
        from datetime import timedelta
        
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        base_qs = wallet.transactions.filter(type='off_app_sale', status='completed')
        
        # Today's Sales
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sales = base_qs.filter(created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0.0
        
        # Weekly Sales (Past 7 days)
        week_start = timezone.now() - timedelta(days=7)
        weekly_sales = base_qs.filter(created_at__gte=week_start).aggregate(total=Sum('amount'))['total'] or 0.0
        
        # All Time Sales
        all_time_sales = base_qs.aggregate(total=Sum('amount'))['total'] or 0.0

        return Response({
            "today_sales": today_sales,
            "weekly_sales": weekly_sales,
            "all_time_sales": all_time_sales,
            "currency": wallet.currency
        })

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiate a wallet funding transaction via Paystack.
        """
        amount = request.data.get('amount')
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        service = PaystackService()
        metadata = {
            "user_id": str(request.user.id),
            "type": "wallet_funding"
        }
        
        # In a real scenario, you might want to specify a callback URL
        # e.g., request.build_absolute_uri('/payments/verify-ui/')
        
        response = service.initialize_transaction(
            email=request.user.email,
            amount=amount,
            metadata=metadata
        )
        
        if response.get('status'):
            data = response.get('data')
            reference = data.get('reference')
            
            # Create a pending transaction record
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                type='deposit',
                reference_id=reference,
                status='pending',
                description="Wallet funding via Paystack"
            )
            
            return Response({
                "checkout_url": data.get('authorization_url'),
                "reference": reference
            })
            
        return Response({
            "error": "Could not initialize payment",
            "message": response.get('message')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='verify/(?P<reference>[^/.]+)')
    def verify(self, request, reference=None):
        """
        Verify a wallet funding transaction.
        """
        if not reference:
            return Response({"error": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            tx = Transaction.objects.get(reference_id=reference)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if tx.status == 'completed':
            return Response({"message": "Transaction already completed", "status": "success"})

        service = PaystackService()
        response = service.verify_transaction(reference)
        
        if response.get('status') and response.get('data', {}).get('status') == 'success':
            with transaction.atomic():
                # Update transaction
                tx.status = 'completed'
                tx.save()
                
                # Update wallet balance
                wallet = tx.wallet
                wallet.balance += tx.amount
                wallet.save()
                
            return Response({
                "message": "Wallet funded successfully",
                "new_balance": wallet.balance,
                "status": "success"
            })
            
        return Response({
            "error": "Payment verification failed",
            "message": response.get('message', 'Transaction was not successful')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        # Placeholder for Paystack webhook - requires signature verification
        return Response({"status": "received"})
