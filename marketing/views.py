from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Campaign, PromoCode
from .serializers import CampaignSerializer, PromoCodeSerializer

class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campaign.objects.filter(status='ACTIVE')
    serializer_class = CampaignSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def active(self, request):
        campaigns = Campaign.objects.filter(status='ACTIVE')
        serializer = self.get_serializer(campaigns, many=True)
        return Response(serializer.data)

class PromoCodeViewSet(viewsets.ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

from rest_framework.views import APIView

class ReferralStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'profile'):
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        profile = request.user.profile
        return Response({
            "referralCount": profile.total_referrals,
            "totalEarned": profile.total_referral_earnings
        })
