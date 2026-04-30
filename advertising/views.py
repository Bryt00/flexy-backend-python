from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import models
from .models import AdBooking, AdAnalytics
from django.shortcuts import redirect, get_object_or_404
import random
import uuid

class ActiveAdsAPIView(APIView):
    """
    Public endpoint strictly for the Flutter mobile app.
    Returns all ads that have status='LIVE' for the current week.
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        today = timezone.localdate()
        app_type = request.query_params.get('app_type', '').upper()
        
        live_ads = AdBooking.objects.filter(
            status='LIVE',
            week_start_date__lte=today
        ).order_by('-amount')
        
        if app_type in ['PASSENGER', 'DRIVER']:
            live_ads = live_ads.filter(models.Q(target_audience='ALL') | models.Q(target_audience=app_type))
        
        data = []
        for ad in live_ads:
            # Randomly select variant if variant B exists
            variant = 'A'
            if ad.headline_b and random.choice([True, False]):
                variant = 'B'
                
            headline = ad.headline_b if variant == 'B' and ad.headline_b else ad.headline
            body_text = ad.body_text_b if variant == 'B' and ad.body_text_b else ad.body_text
            image = ad.image_b if variant == 'B' and ad.image_b else ad.image
            
            # Use relative URL for our redirect tracker instead of actual target_url
            target_url = request.build_absolute_uri(f'/api/advertising/click/{ad.id}/?variant={variant}') if ad.target_url else None
            
            data.append({
                'id': str(ad.id),
                'business_name': ad.business_name,
                'headline': headline,
                'body_text': body_text,
                'image_url': request.build_absolute_uri(image.url) if image else None,
                'target_url': target_url,
                'variant': variant,
            })
            
        return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)

class AdImpressionAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    
    def post(self, request):
        ad_id = request.data.get('ad_id')
        variant = request.data.get('variant', 'A')
        
        if not ad_id:
            return Response({'error': 'ad_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            analytics = AdAnalytics.objects.get(ad_booking__id=uuid.UUID(ad_id))
            if variant == 'B':
                analytics.impressions_b += 1
            else:
                analytics.impressions_a += 1
            analytics.save()
            return Response({'status': 'logged'})
        except (AdAnalytics.DoesNotExist, ValueError):
            return Response({'error': 'invalid ad_id'}, status=status.HTTP_404_NOT_FOUND)

class AdClickRedirectView(APIView):
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, ad_id):
        variant = request.query_params.get('variant', 'A')
        ad = get_object_or_404(AdBooking, id=ad_id)
        
        try:
            analytics = ad.analytics
            if variant == 'B':
                analytics.clicks_b += 1
            else:
                analytics.clicks_a += 1
            analytics.save()
        except Exception:
            pass # Failsafe
            
        if ad.target_url:
            return redirect(ad.target_url)
        return Response({'error': 'No URL provided'}, status=status.HTTP_400_BAD_REQUEST)
