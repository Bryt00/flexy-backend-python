from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from core_auth.cache_utils import conditional_api_response
from .models import Campaign, PromoCode
from .serializers import CampaignSerializer, PromoCodeSerializer

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers


@extend_schema_view(
    list=extend_schema(tags=['Marketing'], summary='List active campaigns', description='Returns all active marketing campaigns.'),
    retrieve=extend_schema(tags=['Marketing'], summary='Get campaign details', description='Returns details of a specific campaign.'),
)
class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    """Marketing campaigns viewset."""
    queryset = Campaign.objects.filter(status='ACTIVE')
    serializer_class = CampaignSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)

    @extend_schema(
        tags=['Marketing'],
        summary='Get active campaigns list',
        description='Returns all currently active promotional campaigns.',
        responses={200: CampaignSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        queryset = Campaign.objects.filter(status='ACTIVE')
        return conditional_api_response(request, queryset, self.serializer_class)


@extend_schema_view(
    list=extend_schema(tags=['Marketing'], summary='List promo codes', description='Returns promo codes available to the user.'),
    retrieve=extend_schema(tags=['Marketing'], summary='Get promo code details', description='Returns details of a specific promo code.'),
    create=extend_schema(tags=['Marketing'], summary='Create promo code', description='Creates a new promo code (Admin only).'),
    update=extend_schema(tags=['Marketing'], summary='Update promo code', description='Updates a promo code.'),
    partial_update=extend_schema(tags=['Marketing'], summary='Partially update promo code', description='Partially updates a promo code.'),
    destroy=extend_schema(tags=['Marketing'], summary='Delete promo code', description='Deletes a promo code.'),
)
class PromoCodeViewSet(viewsets.ModelViewSet):
    """Promotional promo code management."""
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReferralStatsView(APIView):
    """Returns the authenticated user's referral statistics."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Marketing'],
        summary='Get referral statistics',
        description=(
            'Returns referral performance stats for the authenticated user:\n'
            '- Total friends referred (`referralCount` / `referral_count`)\n'
            '- Total earnings from referrals (`totalEarned` / `total_earned`) in GHS\n\n'
            'Supports both camelCase and snake_case keys for Flutter compatibility.'
        ),
        responses={
            200: inline_serializer(
                name='ReferralStatsResponse',
                fields={
                    'referralCount': drf_serializers.IntegerField(),
                    'referral_count': drf_serializers.IntegerField(),
                    'totalEarned': drf_serializers.FloatField(),
                    'total_earned': drf_serializers.FloatField(),
                }
            ),
            404: OpenApiResponse(description='Profile not found.'),
        },
    )
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
