from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer

class PaymentViewSet(viewsets.GenericViewSet):
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

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        # Placeholder for Paystack initiation
        amount = request.data.get('amount')
        return Response({
            "status": "success",
            "message": "Payment initiation placeholder",
            "authorization_url": "https://paystack.com/auth/placeholder",
            "reference": "ref_12345"
        })

    @action(detail=False, methods=['get'], url_path='verify/(?P<reference>[^/.]+)')
    def verify(self, request, reference=None):
        # Placeholder for Paystack verification
        return Response({
            "status": "success",
            "message": f"Verified reference {reference}"
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        # Placeholder for Paystack webhook
        return Response({"status": "received"})
