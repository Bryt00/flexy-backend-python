from django.db import models
from django.conf import settings
from django.utils import timezone
from notification.utils import send_notification
from integrations.email_service import EmailService

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    emergency_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    rating = models.FloatField(default=0.0)
    
    # Loyalty & Engagement Metrics
    tier = models.CharField(max_length=20, default='Silver')
    points = models.IntegerField(default=0)
    acceptance_rate = models.FloatField(default=100.0)
    cancellation_rate = models.FloatField(default=0.0)
    total_rides = models.IntegerField(default=0)
    
    # Real-time Location Tracking for matching
    last_lat = models.FloatField(blank=True, null=True)
    last_lng = models.FloatField(blank=True, null=True)
    
    # GeoDjango Point for high-performance spatial queries
    # Sync with last_lat/last_lng in save()
    if settings.USE_GIS:
        from django.contrib.gis.db import models as gis_models
        last_location_point = gis_models.PointField(null=True, blank=True, srid=4326)
    else:
        last_location_point = models.TextField(null=True, blank=True)

    last_location_update = models.DateTimeField(blank=True, null=True)
    is_online = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Matching & Reliability Metrics
    missed_opportunities_count = models.IntegerField(default=0)

    # Referral System
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True, db_index=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    total_referrals = models.IntegerField(default=0)
    total_referral_earnings = models.FloatField(default=0.0)

    # Preferences & Security
    notification_preferences = models.JSONField(default=dict, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random
            import string
            # Generate a 6-character random code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            # Ensure it's unique
            self.referral_code = f"FLX-{code}"
        
        # Automatically sync PointField if GIS is enabled
        if settings.USE_GIS and self.last_lat and self.last_lng:
            from django.contrib.gis.geos import Point
            self.last_location_point = Point(self.last_lng, self.last_lat)
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.user.email

class DriverVerification(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUBMITTED', 'Submitted'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    )
    
    RIDE_CATEGORY_CHOICES = (
        ('none', 'Not Assigned'),
        ('go', 'Flexy Go'),
        ('comfort', 'Flexy Comfort'),
        ('xl', 'Flexy XL'),
        ('exec', 'Flexy Executive'),
        ('pragya', 'Flexy Pragya'),
    )
    
    driver = models.OneToOneField(Profile, on_delete=models.CASCADE, primary_key=True, related_name='verification')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    license_url = models.TextField(blank=True, null=True)
    id_card_url = models.TextField(blank=True, null=True)
    insurance_url = models.TextField(blank=True, null=True)
    roadworthy_url = models.TextField(blank=True, null=True)
    vehicle_video_url = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_category = models.CharField(
        max_length=20, 
        choices=RIDE_CATEGORY_CHOICES, 
        default='none',
        help_text="Category assigned to the driver upon verification"
    )
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    rejected_reason = models.TextField(blank=True, null=True)

    def approve(self):
        """
        Approves the verification and synchronizes related models (Vehicles, Subscriptions).
        """
        from django.apps import apps
        from django.utils import timezone
        
        self.status = 'VERIFIED'
        self.is_verified = True
        self.verified_at = timezone.now()
        self.rejected_reason = None
        self.save()

        # 1. Sync Vehicles
        Vehicle = apps.get_model('vehicles', 'Vehicle')
        vehicles = Vehicle.objects.filter(driver=self.driver)
        
        # Determine the vehicle type based on assigned category
        vehicle_type = self.assigned_category if self.assigned_category != 'none' else 'go'
        
        vehicles.update(
            is_verified=True,
            is_active=True,
            type=vehicle_type
        )

        # 2. Sync Subscription with 14-day Free Trial
        DriverSubscription = apps.get_model('subscriptions', 'DriverSubscription')
        sub, created = DriverSubscription.objects.get_or_create(profile=self.driver)
        if not sub.is_trial_used:
            sub.trial_end_date = timezone.now() + timezone.timedelta(days=14)
            sub.is_trial_used = True
            sub.save()

        # 3. Notify the user
        title = "Account Verified!"
        body = "Congratulations! Your driver account has been approved. You can now start earning."
        send_notification(self.driver.user, title, body, type='PUSH')
        EmailService.send_verification_status_email(self.driver.user, is_approved=True)

        return True

    def reject(self, reason=None):
        """
        Rejects the verification and deactivates related vehicles.
        """
        from django.apps import apps
        
        self.status = 'REJECTED'
        self.is_verified = False
        self.verified_at = None
        if reason:
            self.rejected_reason = reason
        self.save()

        # Deactivate vehicles
        Vehicle = apps.get_model('vehicles', 'Vehicle')
        Vehicle.objects.filter(driver=self.driver).update(
            is_verified=False,
            is_active=False
        )

        # Notify the user
        title = "Verification Update"
        body = f"Your verification docs need review: {reason}" if reason else "Your verification was not approved. Please check your documents."
        send_notification(self.driver.user, title, body, type='PUSH')
        EmailService.send_verification_status_email(self.driver.user, is_approved=False, reason=reason)

        return True

    def __str__(self):
        return f"Verification for {self.driver.user.email}"
