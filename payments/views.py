import json
import hmac
import hashlib
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.conf import settings
from django.utils import timezone
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer
from integrations.paystack import PaystackService

from drf_spectacular.utils import extend_schema, OpenApiTypes
from core_auth.cache_utils import cached_api_response, invalidate_user_cache

logger = logging.getLogger(__name__)

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
            from django.db.models import Sum
            from django.utils import timezone
            from datetime import timedelta
            from rides.models import Ride
            from courier.models import Delivery
            from .models import Wallet, DriverEarningsSummary
            
            user = request.user
            wallet, _ = Wallet.objects.get_or_create(user=user)
            
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            month_start = now - timedelta(days=30)
            
            # 1. Ride Aggregates
            ride_qs = Ride.objects.filter(driver=user, status='completed')
            today_ride_earnings = ride_qs.filter(created_at__gte=today_start).aggregate(s=Sum('fare'))['s'] or 0.0
            weekly_ride_earnings = ride_qs.filter(created_at__gte=week_start).aggregate(s=Sum('fare'))['s'] or 0.0
            monthly_ride_earnings = ride_qs.filter(created_at__gte=month_start).aggregate(s=Sum('fare'))['s'] or 0.0
            
            today_ride_count = ride_qs.filter(created_at__gte=today_start).count()
            weekly_ride_count = ride_qs.filter(created_at__gte=week_start).count()
            monthly_ride_count = ride_qs.filter(created_at__gte=month_start).count()
            
            # 2. Delivery Aggregates
            delivery_qs = Delivery.objects.filter(driver__user=user, status='DELIVERED')
            today_deliv_earnings = delivery_qs.filter(created_at__gte=today_start).aggregate(s=Sum('final_fare'))['s'] or 0.0
            weekly_deliv_earnings = delivery_qs.filter(created_at__gte=week_start).aggregate(s=Sum('final_fare'))['s'] or 0.0
            monthly_deliv_earnings = delivery_qs.filter(created_at__gte=month_start).aggregate(s=Sum('final_fare'))['s'] or 0.0
            
            today_deliv_count = delivery_qs.filter(created_at__gte=today_start).count()
            weekly_deliv_count = delivery_qs.filter(created_at__gte=week_start).count()
            monthly_deliv_count = delivery_qs.filter(created_at__gte=month_start).count()
            
            # 3. Cancelled Count
            cancelled_rides_count = Ride.objects.filter(driver=user, status='cancelled').count() + Delivery.objects.filter(driver__user=user, status='CANCELLED').count()
            
            # 4. Driver Rating
            rating = 5.0
            if hasattr(user, 'profile') and user.profile.rating > 0:
                rating = round(user.profile.rating, 1)
                
            today_total = float(today_ride_earnings + today_deliv_earnings)
            weekly_total = float(weekly_ride_earnings + weekly_deliv_earnings)
            monthly_total = float(monthly_ride_earnings + monthly_deliv_earnings)
            
            # 5. Sync DriverEarningsSummary for legacy / caching callers
            summary, _ = DriverEarningsSummary.objects.get_or_create(user=user)
            summary.today_sales = today_total
            summary.weekly_sales = weekly_total
            summary.total_sales = float(ride_qs.aggregate(s=Sum('fare'))['s'] or 0.0) + float(delivery_qs.aggregate(s=Sum('final_fare'))['s'] or 0.0)
            summary.ride_count = ride_qs.count() + delivery_qs.count()
            summary.save()
            
            return Response({
                "daily": {
                    "total_earnings": today_total,
                    "ride_count": today_ride_count,
                    "delivery_count": today_deliv_count
                },
                "weekly": {
                    "total_earnings": weekly_total,
                    "ride_count": weekly_ride_count,
                    "delivery_count": weekly_deliv_count
                },
                "monthly": {
                    "total_earnings": monthly_total, 
                    "ride_count": monthly_ride_count,
                    "delivery_count": monthly_deliv_count
                },
                "stats": {
                    "total_distance": round(today_total * 0.8, 1),
                    "rating": rating,
                    "cancelled_rides": cancelled_rides_count,
                    "online_hours": "Active"
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
        """
        Paystack Webhook Handler with HMAC-SHA512 signature verification.
        Validates event signature and fulfills charge.success events for wallet funding.
        """
        paystack_signature = request.headers.get('x-paystack-signature') or request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        if not paystack_signature:
            return Response({"error": "Missing x-paystack-signature header"}, status=status.HTTP_400_BAD_REQUEST)

        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not secret_key:
            return Response({"error": "Paystack secret key is not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Verify HMAC-SHA512 Signature over raw body
        computed_signature = hmac.new(
            secret_key.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed_signature.lower(), paystack_signature.lower()):
            logger.warning(f"Paystack webhook signature mismatch! Header: {paystack_signature}")
            return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return Response({"error": "Invalid JSON body"}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event')
        data = payload.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference')
            if reference:
                try:
                    with transaction.atomic():
                        tx = Transaction.objects.select_for_update().filter(
                            models.Q(paystack_reference=reference) | models.Q(id=reference)
                        ).first()

                        if tx and tx.status != 'completed':
                            tx.status = 'completed'
                            tx.payment_status = 'completed'
                            tx.save()

                            wallet = tx.wallet
                            wallet.balance += tx.amount
                            wallet.save()

                            # Invalidate user payment & wallet caches
                            invalidate_user_cache(wallet.user.id, 'wallet')
                            invalidate_user_cache(wallet.user.id, 'earnings')
                            invalidate_user_cache(wallet.user.id, 'pay_stats')
                            logger.info(f"Paystack webhook: Successfully funded wallet for user {wallet.user.email} with GHS {tx.amount}")
                except Exception as e:
                    logger.error(f"Error executing Paystack webhook fulfillment for reference {reference}: {e}")

        return Response({"status": "success", "event": event}, status=status.HTTP_200_OK)
