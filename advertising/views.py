from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import AdBooking

class ActiveAdsAPIView(APIView):
    """
    Public endpoint strictly for the Flutter mobile app.
    Returns all ads that have status='LIVE' for the current week.
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        today = timezone.localdate()
        
        live_ads = AdBooking.objects.filter(
            status='LIVE',
            week_start_date__lte=today
        ).order_by('-amount') # Potentially sort by how much they paid if there's tiered bidding
        
        data = []
        for ad in live_ads:
            data.append({
                'id': str(ad.id),
                'business_name': ad.business_name,
                'headline': ad.headline,
                'body_text': ad.body_text,
                'image_url': request.build_absolute_uri(ad.image.url) if ad.image else None,
                'target_url': ad.target_url,
            })
            
        return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)
