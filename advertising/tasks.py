from celery import shared_task
from django.utils import timezone
from .models import AdBooking, AdExtension
from integrations.email_service import EmailService

@shared_task
def transition_ads_to_live():
    """Runs Monday early morning — APPROVED+PAID → LIVE"""
    today = timezone.localdate()
    # Find bookings that start today or earlier and are APPROVED/PAID
    bookings_to_live = AdBooking.objects.filter(
        status='APPROVED',
        payment_status='PAID',
        week_start_date__lte=today
    )
    count = bookings_to_live.update(status='LIVE')
    return f"Moved {count} ads to LIVE."

@shared_task
def expire_completed_ads():
    """Runs Sunday night — LIVE past end date → COMPLETED"""
    today = timezone.localdate()
    # If today is >= the end of the week (week_start + 6 days = Sunday)
    # We'll just transition anything that was supposed to end yesterday or before
    import datetime
    
    # We find ads where week_start_date + 7 days <= today
    # To do this in the database, we can iterate or use database functions.
    # For simplicity, we iterate if the dataset isn't massive.
    count = 0
    live_ads = AdBooking.objects.filter(status='LIVE')
    for ad in live_ads:
        end_date = ad.week_start_date + datetime.timedelta(days=7)
        if today >= end_date:
            ad.status = 'COMPLETED'
            ad.save()
            count += 1
            
    return f"Moved {count} ads to COMPLETED."

@shared_task
def send_ad_approved_email(booking_id):
    pass # Implementation requires EmailService template mapping

@shared_task
def send_ad_rejected_email(booking_id):
    pass

@shared_task
def send_ad_confirmation_email(booking_id):
    pass
