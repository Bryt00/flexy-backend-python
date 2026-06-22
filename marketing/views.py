from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core_auth.cache_utils import conditional_api_response
from .models import Campaign, PromoCode
from .serializers import CampaignSerializer, PromoCodeSerializer

class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campaign.objects.filter(status='ACTIVE')
    serializer_class = CampaignSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)

    @action(detail=False, methods=['get'])
    def active(self, request):
        queryset = Campaign.objects.filter(status='ACTIVE')
        return conditional_api_response(request, queryset, self.serializer_class)

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
            "referral_count": profile.total_referrals,
            "totalEarned": profile.total_referral_earnings,
            "total_earned": profile.total_referral_earnings
        })
