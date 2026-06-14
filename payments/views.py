from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer
from integrations.paystack import PaystackService

from drf_spectacular.utils import extend_schema, OpenApiTypes
from core_auth.cache_utils import cached_api_response, invalidate_user_cache

class PaymentViewSet(viewsets.GenericViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def wallet(self, request):
        def fetch_wallet():
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data)
        return cached_api_response(request, 'wallet', timeout=120, fetcher=fetch_wallet)

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        txs = wallet.transactions.all().order_by('-created_at')
        
        page = paginator.paginate_queryset(txs, request)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = TransactionSerializer(txs, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def earnings(self, request):
        def fetch_earnings():
            from .models import DriverEarningsSummary
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            summary, _ = DriverEarningsSummary.objects.get_or_create(user=request.user)
            return Response({
                "daily": {
                    "total_earnings": summary.today_sales,
                    "ride_count": summary.ride_count,
                    "delivery_count": 0
                },
                "weekly": {
                    "total_earnings": summary.weekly_sales,
                    "ride_count": summary.ride_count,
                    "delivery_count": 0
                },
                "monthly": {
                    "total_earnings": summary.weekly_sales * 4, 
                    "ride_count": summary.ride_count,
                    "delivery_count": 0
                },
                "stats": {
                    "total_distance": float(summary.total_sales) * 0.8,
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
        return cached_api_response(request, 'earnings', timeout=300, fetcher=fetch_earnings)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def stats(self, request):
        def fetch_stats():
            from .models import DriverEarningsSummary
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            summary, _ = DriverEarningsSummary.objects.get_or_create(user=request.user)
            return Response({
                "today_sales": summary.today_sales,
                "weekly_sales": summary.weekly_sales,
                "total_sales": summary.total_sales,
                "currency": wallet.currency
            })
        return cached_api_response(request, 'pay_stats', timeout=300, fetcher=fetch_stats)

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
            # Invalidate wallet/earnings caches after funding
            invalidate_user_cache(request.user.id, 'wallet')
            invalidate_user_cache(request.user.id, 'earnings')
            invalidate_user_cache(request.user.id, 'pay_stats')
            
        return Response({
            "error": "Payment verification failed",
            "message": response.get('message', 'Transaction was not successful')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        # Placeholder for Paystack webhook - requires signature verification
        return Response({"status": "received"})
