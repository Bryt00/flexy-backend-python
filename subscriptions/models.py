import uuid
from django.db import models
from django.utils import timezone
from profiles.models import Profile
from core_settings.models import get_vehicle_categories

class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50, 
        choices=get_vehicle_categories,
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
    
    BILLING_TYPES = (
        ('subscription', 'Subscription'),
        ('commission', 'Per-Ride Commission'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPES, default='subscription')
    last_billing_switch_date = models.DateTimeField(null=True, blank=True)
    outstanding_cash_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    has_unpaid_cash_debt = models.BooleanField(default=False)
    
    start_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    
    trial_end_date = models.DateTimeField(null=True, blank=True)
    is_trial_used = models.BooleanField(default=False)
    
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_in_trial(self):
        from django.utils import timezone
        if not self.trial_end_date:
            return False
        return self.trial_end_date > timezone.now()

    @property
    def trial_days_remaining(self):
        from django.utils import timezone
        if not self.is_in_trial:
            return 0
        diff = self.trial_end_date - timezone.now()
        return max(0, diff.days)

    @property
    def commission_rate(self):
        """
        14-day trial applies to both models (0% commission during trial).
        Commission model applies current CommissionRule percentage (default 10%).
        Subscription model pays 0% commission on rides.
        """
        if self.is_in_trial:
            return 0.0
        if self.billing_type == 'commission':
            from core_settings.models import CommissionRule
            return CommissionRule.get_current_rate()
        return 0.0

    @property
    def can_switch_billing_type(self):
        """
        Driver can switch billing model once every 6 months after active plan expiration.
        """
        if not self.last_billing_switch_date:
            return True
        from django.utils import timezone
        cooldown = self.last_billing_switch_date + timezone.timedelta(days=180)
        return timezone.now() >= cooldown

    @property
    def is_currently_active(self):
        from django.utils import timezone
        if self.is_in_trial:
            return True
        if self.billing_type == 'commission':
            return not self.has_unpaid_cash_debt
        if self.status != 'active':
            return False
        if self.expiry_date and self.expiry_date < timezone.now():
            return False
        return True

    @property
    def is_expired(self):
        if self.billing_type == 'commission':
            return False
        from django.utils import timezone
        return self.expiry_date and self.expiry_date < timezone.now()

    @property
    def is_in_grace_period(self):
        if self.billing_type == 'commission':
            return False
        if not self.is_expired:
            return False
        from django.utils import timezone
        grace_expiry = self.expiry_date + timezone.timedelta(hours=24)
        return timezone.now() < grace_expiry

    @property
    def can_go_online(self):
        """
        Billing gating rules:
        1. 1-Ride Cash Debt Policy: If driver owes unpaid cash commission debt, they are blocked.
        2. Commission model: Allowed online if no debt.
        3. Subscription model: Allowed if in trial or active and unexpired.
        """
        if self.has_unpaid_cash_debt or self.outstanding_cash_debt > 0:
            return False

        if self.billing_type == 'commission':
            return True

        if self.is_in_trial:
            return True
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
