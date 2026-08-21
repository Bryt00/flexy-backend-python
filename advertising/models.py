from django.db import models
from django.utils import timezone
import uuid
import datetime
from solo.models import SingletonModel

class AdSlotCapacity(SingletonModel):
    """Admin-editable platform-wide config."""
    max_ads_per_week = models.IntegerField(default=4)
    price_per_week_ghs = models.DecimalField(max_digits=8, decimal_places=2, default=150.00)

    def __str__(self):
        return "Ad Slot Configuration"

    class Meta:
        verbose_name = "Ad Slot Capacity"

class AdBooking(models.Model):
    STATUS = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('LIVE', 'Live'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]
    PAYMENT_STATUS = [
        ('UNPAID', 'Unpaid'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    ]
    AUDIENCE_CHOICES = [
        ('ALL', 'All Users'),
        ('DRIVER', 'Drivers Only'),
        ('PASSENGER', 'Passengers Only'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    headline = models.CharField(max_length=80)
    body_text = models.TextField(max_length=500)
    image = models.ImageField(upload_to='ads/', blank=True, null=True)
    target_url = models.URLField(blank=True, null=True)
    
    target_audience = models.CharField(choices=AUDIENCE_CHOICES, default='ALL', max_length=20)
    
    headline_b = models.CharField(max_length=80, blank=True, null=True)
    body_text_b = models.TextField(max_length=500, blank=True, null=True)
    image_b = models.ImageField(upload_to='ads/', blank=True, null=True)
    
    week_start_date = models.DateField() # Should always be a Monday
    
    status = models.CharField(choices=STATUS, default='PENDING_REVIEW', max_length=20)
    rejection_reason = models.TextField(blank=True, null=True)
    
    payment_status = models.CharField(choices=PAYMENT_STATUS, default='UNPAID', max_length=20)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    
    dashboard_token = models.CharField(max_length=255, blank=True)
    paystack_checkout_url = models.URLField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.dashboard_token:
            from django.core.signing import TimestampSigner
            signer = TimestampSigner()
            self.dashboard_token = signer.sign(str(self.id))
        super().save(*args, **kwargs)
        if self.image:
            self._process_image(self.image.path)
        if self.image_b:
            self._process_image(self.image_b.path)

    def _process_image(self, image_path):
        from PIL import Image
        import os

        try:
            img = Image.open(image_path)
            # Target ratio 2:1 (e.g. 800x400)
            target_width = 800
            target_height = 400
            
            width, height = img.size
            img_ratio = width / height
            target_ratio = target_width / target_height

            if img_ratio > target_ratio:
                # Image is too wide, crop sides
                new_width = int(target_ratio * height)
                left = (width - new_width) / 2
                img = img.crop((left, 0, left + new_width, height))
            else:
                # Image is too tall, crop top/bottom
                new_height = int(width / target_ratio)
                top = (height - new_height) / 2
                img = img.crop((0, top, width, top + new_height))

            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            img.save(image_path, quality=90, optimize=True)
        except Exception as e:
            print(f"Error processing image: {e}")

    @classmethod
    def slots_available_for_week(cls, week_start):
        cap = AdSlotCapacity.get_solo().max_ads_per_week
        booked = cls.objects.filter(
            week_start_date=week_start,
            status__in=['PENDING_REVIEW', 'APPROVED', 'LIVE']
        ).count()
        return max(0, cap - booked)

    @classmethod
    def next_available_weeks(cls, count=8):
        """Returns list of {week_start, slots_remaining, is_full} for coming weeks."""
        from django.utils import timezone
        
        # Start from the next Monday
        today = timezone.localdate()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0: # Target next Monday
            days_ahead += 7
        
        current_monday = today + datetime.timedelta(days=days_ahead)
        available_weeks = []
        
        for i in range(count):
            target_week = current_monday + datetime.timedelta(days=i*7)
            slots = cls.slots_available_for_week(target_week)
            available_weeks.append({
                'week_start': target_week,
                'slots_remaining': slots,
                'is_full': slots <= 0
            })
            
        return available_weeks

    def __str__(self):
        return f"{self.business_name} - {self.week_start_date} ({self.status})"

class AdExtension(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_booking = models.ForeignKey(AdBooking, on_delete=models.CASCADE, related_name='extensions')
    extended_week_start = models.DateField()
    status = models.CharField(choices=AdBooking.STATUS, default='APPROVED', max_length=20)
    payment_status = models.CharField(choices=AdBooking.PAYMENT_STATUS, default='UNPAID', max_length=20)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    paystack_checkout_url = models.URLField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extension for {self.original_booking.business_name} to {self.extended_week_start}"

class AdAnalytics(models.Model):
    ad_booking = models.OneToOneField(AdBooking, on_delete=models.CASCADE, related_name='analytics')
    impressions_a = models.PositiveIntegerField(default=0)
    clicks_a = models.PositiveIntegerField(default=0)
    impressions_b = models.PositiveIntegerField(default=0)
    clicks_b = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.ad_booking.business_name}"

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(post_save, sender=AdBooking)
def create_ad_analytics(sender, instance, created, **kwargs):
    if created:
        AdAnalytics.objects.create(ad_booking=instance)

@receiver(pre_save, sender=AdBooking)
def handle_ad_status_change(sender, instance, **kwargs):
    from django.core.signing import TimestampSigner
    signer = TimestampSigner()

    if not instance.dashboard_token:
        instance.dashboard_token = signer.sign(str(instance.id))

    if instance.id:
        try:
            old_instance = AdBooking.objects.get(id=instance.id)
            status_changed = old_instance.status != instance.status
        except AdBooking.DoesNotExist:
            status_changed = True

        if status_changed:
            # Always regenerate dashboard token on status change so emailed links are fresh
            instance.dashboard_token = signer.sign(str(instance.id))

            from integrations.email_service import EmailService
            
            if instance.status == 'APPROVED':
                # Initialize Paystack hosted checkout transaction
                payment_url = _initialize_ad_payment(instance)
                
                EmailService.send_ad_status_email(
                    contact_email=instance.contact_email,
                    business_name=instance.business_name,
                    is_approved=True,
                    dashboard_token=instance.dashboard_token,
                    payment_url=payment_url
                )
            elif instance.status == 'REJECTED':
                reason = instance.rejection_reason or "Creative does not meet our guidelines."
                EmailService.send_ad_status_email(
                    contact_email=instance.contact_email,
                    business_name=instance.business_name,
                    is_approved=False,
                    reason=reason,
                    dashboard_token=instance.dashboard_token
                )


def _initialize_ad_payment(ad_booking):
    """
    Initializes a Paystack hosted checkout transaction for an approved ad booking.
    Returns the checkout URL or None on failure.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from integrations.paystack import PaystackService
        from django.conf import settings
        
        paystack = PaystackService()
        site_url = getattr(settings, 'SITE_URL', 'https://flexyridegh.com').rstrip('/')
        callback_url = f"{site_url}/advertise/payment/callback/"
        
        result = paystack.initialize_transaction(
            email=ad_booking.contact_email,
            amount=ad_booking.amount,
            callback_url=callback_url,
            metadata={
                'ad_id': str(ad_booking.id),
                'type': 'ad_booking',
                'business_name': ad_booking.business_name,
                'custom_fields': [
                    {
                        'display_name': 'Business Name',
                        'variable_name': 'business_name',
                        'value': ad_booking.business_name,
                    },
                    {
                        'display_name': 'Ad Headline',
                        'variable_name': 'ad_headline',
                        'value': ad_booking.headline,
                    },
                ]
            }
        )
        
        if result.get('status'):
            data = result.get('data', {})
            checkout_url = data.get('authorization_url', '')
            reference = data.get('reference', '')
            
            ad_booking.paystack_checkout_url = checkout_url
            ad_booking.paystack_reference = reference
            
            logger.info(f"Paystack checkout initialized for ad {ad_booking.id}: {checkout_url}")
            return checkout_url
        else:
            logger.error(f"Failed to initialize Paystack checkout for ad {ad_booking.id}: {result.get('message')}")
            return None
    except Exception as e:
        logger.error(f"Exception initializing Paystack checkout for ad {ad_booking.id}: {e}")
        return None
