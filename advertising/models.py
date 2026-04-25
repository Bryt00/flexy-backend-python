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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    headline = models.CharField(max_length=80)
    body_text = models.TextField(max_length=500)
    image = models.ImageField(upload_to='ads/', blank=True, null=True)
    target_url = models.URLField(blank=True, null=True)
    
    week_start_date = models.DateField() # Should always be a Monday
    
    status = models.CharField(choices=STATUS, default='PENDING_REVIEW', max_length=20)
    rejection_reason = models.TextField(blank=True, null=True)
    
    payment_status = models.CharField(choices=PAYMENT_STATUS, default='UNPAID', max_length=20)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    
    dashboard_token = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extension for {self.original_booking.business_name} to {self.extended_week_start}"
