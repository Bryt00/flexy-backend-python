import uuid
from django.db import models
from django.utils import timezone
from profiles.models import Profile

class SubscriptionPlan(models.Model):
    CATEGORY_CHOICES = (
        ('go', 'Flexy Go'),
        ('comfort', 'Flexy Comfort'),
        ('xl', 'Flexy XL'),
        ('exec', 'Flexy Executive'),
        ('pragya', 'Flexy Pragya'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES,
        help_text="The vehicle category this plan applies to"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.category}) - GH₵ {self.price}"

class DriverSubscription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending_payment', 'Pending Payment'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    
    start_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_currently_active(self):
        from django.utils import timezone
        if self.status != 'active':
            return False
        if self.expiry_date and self.expiry_date < timezone.now():
            return False
        return True

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date and self.expiry_date < timezone.now()

    @property
    def is_in_grace_period(self):
        if not self.is_expired:
            return False
        from django.utils import timezone
        grace_expiry = self.expiry_date + timezone.timedelta(hours=24)
        return timezone.now() < grace_expiry

    @property
    def can_go_online(self):
        """
        Strict: must NOT be expired to be visible.
        Once month is due, they are blocked from being visible.
        """
        return self.status == 'active' and not self.is_expired

    @property
    def grace_period_remaining(self):
        if not self.is_in_grace_period:
            return None
        from django.utils import timezone
        grace_expiry = self.expiry_date + timezone.timedelta(hours=24)
        diff = grace_expiry - timezone.now()
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def __str__(self):
        return f"Subscription for {self.profile.user.email} - {self.status}"

class SubscriptionPayment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(DriverSubscription, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paystack_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    payment_date = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.paystack_reference} - {self.status}"
