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
        import datetime
        today = timezone.localdate()
        app_type = request.query_params.get('app_type', '').upper()
        
        # Enforce 14 days display limit dynamically
        live_ads = AdBooking.objects.filter(
            status='LIVE',
            week_start_date__lte=today,
            week_start_date__gte=today - datetime.timedelta(days=14)
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
            
            # Enhancement: Give the app the DIRECT URL for a better user experience,
            # but provide a tracking_url for a background "ping" to log the click.
            target_url = ad.target_url
            if target_url and not target_url.startswith(('http://', 'https://')):
                target_url = f'https://{target_url}'

            tracking_url = request.build_absolute_uri(f'/api/advertising/click/{ad.id}/?variant={variant}') if ad.target_url else None
            
            data.append({
                'id': str(ad.id),
                'business_name': ad.business_name,
                'headline': headline,
                'body_text': body_text,
                'image_url': request.build_absolute_uri(image.url) if image else None,
                'target_url': target_url,
                'tracking_url': tracking_url, # For background logging
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
            url = ad.target_url
            # Safety: Ensure the URL starts with a scheme so it doesn't redirect to a local path
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            return redirect(url)
        return Response({'error': 'No URL provided'}, status=status.HTTP_400_BAD_REQUEST)

from django.conf import settings
from django.core.mail import send_mail
from integrations.paystack import PaystackService
from .models import AdExtension

class VerifyAdPaymentAPIView(APIView):
    """
    Endpoint for verifying Paystack ad booking and campaign extension payments.
    """
    authentication_classes = []
    permission_classes = []
    
    def post(self, request):
        reference = request.data.get('reference')
        ad_id = request.data.get('ad_id')
        extension_id = request.data.get('extension_id')
        
        if not reference:
            return Response({'error': 'reference is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            paystack_service = PaystackService()
            verification = paystack_service.verify_transaction(reference)
            
            if not verification or verification.get('status') != 'success':
                return Response({'error': 'Transaction verification failed on Paystack.'}, status=status.HTTP_400_BAD_REQUEST)
                
            paid_amount = verification.get('amount') / 100
            
            # 1. Handle Ad Campaign Extensions
            if extension_id:
                extension = AdExtension.objects.get(id=uuid.UUID(extension_id))
                if paid_amount >= float(extension.amount):
                    extension.payment_status = 'PAID'
                    extension.status = 'APPROVED' # Set to approved so Celery task transitions it to LIVE at the week start date
                    extension.paystack_reference = reference
                    extension.save()
                    
                    booking = extension.original_booking
                    
                    # Notify user of successful extension activation
                    subject = f"Ad Campaign Extension Activated: {booking.business_name}"
                    message = f"Hello {booking.business_name},\n\nYour payment has been successfully verified! Your ad campaign '{booking.headline}' has been extended to the week of {extension.extended_week_start}.\n\nYou can track campaign performance in your dashboard:\n{request.build_absolute_uri('/advertise/dashboard/')}?token={booking.dashboard_token}\n\nBest regards,\nThe FlexyRide Team"
                    
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [booking.contact_email],
                            fail_silently=True,
                        )
                    except Exception as email_err:
                        print(f"Failed to send extension activation email: {email_err}")
                        
                    return Response({
                        'status': 'success',
                        'message': 'Extension payment verified successfully!',
                        'dashboard_url': f"/advertise/dashboard/?token={booking.dashboard_token}"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'error': f'Paid amount {paid_amount} is less than required extension amount {extension.amount}'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Handle Ad Bookings
            elif ad_id:
                ad = AdBooking.objects.get(id=uuid.UUID(ad_id))
                if paid_amount >= float(ad.amount):
                    ad.payment_status = 'PAID'
                    ad.status = 'LIVE'
                    ad.paystack_reference = reference
                    ad.save()
                    
                    subject = f"Ad Campaign Activated: {ad.business_name}"
                    message = f"Hello {ad.business_name},\n\nYour payment has been successfully verified! Your ad campaign '{ad.headline}' is now LIVE for the week of {ad.week_start_date}.\n\nYou can track real-time impressions and clicks in your advertising dashboard here:\n{request.build_absolute_uri('/advertise/dashboard/')}?token={ad.dashboard_token}\n\nBest regards,\nThe FlexyRide Team"
                    
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [ad.contact_email],
                            fail_silently=True,
                        )
                    except Exception as email_err:
                        print(f"Failed to send activation email: {email_err}")
                        
                    return Response({
                        'status': 'success',
                        'message': 'Payment successfully verified. Your ad is now LIVE!',
                        'dashboard_url': f"/advertise/dashboard/?token={ad.dashboard_token}"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'error': f'Paid amount {paid_amount} is less than required booking amount {ad.amount}'}, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                return Response({'error': 'Either ad_id or extension_id must be provided.'}, status=status.HTTP_400_BAD_REQUEST)
                
        except (AdBooking.DoesNotExist, AdExtension.DoesNotExist):
            return Response({'error': 'Ad booking or extension record not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

