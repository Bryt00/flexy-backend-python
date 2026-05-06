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
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        base_qs = wallet.transactions.filter(type='off_app_sale', status='completed')
        
        now = timezone.now()
        
        def get_summary(start_date):
            qs = base_qs.filter(created_at__gte=start_date)
            agg = qs.aggregate(
                total=Sum('amount'),
                rides=Count('id')
            )
            return {
                "total_earnings": float(agg['total'] or 0.0),
                "ride_count": agg['rides'] or 0,
                "delivery_count": 0 # Placeholder for now
            }

        # Daily (Since midnight)
        daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily = get_summary(daily_start)
        
        # Weekly (Past 7 days)
        weekly_start = now - timedelta(days=7)
        weekly = get_summary(weekly_start)
        
        # Monthly (Past 30 days)
        monthly_start = now - timedelta(days=30)
        monthly = get_summary(monthly_start)

        # Overall Stats
        overall_agg = base_qs.aggregate(
            total_dist=Sum('amount'), # Placeholder for distance
            rides=Count('id')
        )
        
        return Response({
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "stats": {
                "total_distance": float(overall_agg['total_dist'] or 0.0) * 0.8, # Mock distance
                "rating": 4.9,
                "cancelled_rides": 0,
                "online_hours": "12h 30m"
            },
            "peak_hours": {
                "8": 4, "12": 6, "17": 8, "20": 3
            },
            "balance": float(wallet.balance),
            "currency": wallet.currency
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
        total_sales = base_qs.aggregate(total=Sum('amount'))['total'] or 0.0

        return Response({
            "today_sales": today_sales,
            "weekly_sales": weekly_sales,
            "total_sales": total_sales, # Changed from all_time_sales to total_sales for frontend compatibility
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
