import uuid
from django.db import models
from django.conf import settings
from profiles.models import Profile

class Ride(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('arrived', 'Arrived'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_as_rider', blank=True, null=True)
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_as_driver', blank=True, null=True)
    
    type = models.CharField(max_length=50, blank=True, null=True)
    pickup_address = models.TextField(blank=True, null=True)
    dropoff_address = models.TextField(blank=True, null=True)
    
    pickup_lat = models.FloatField(blank=True, null=True)
    pickup_lng = models.FloatField(blank=True, null=True)
    
    dropoff_lat = models.FloatField(blank=True, null=True)
    dropoff_lng = models.FloatField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    fare = models.FloatField(blank=True, null=True)
    distance = models.FloatField(default=0.0)
    
    # New Fields for Feature Parity & Analytics
    is_scheduled = models.BooleanField(default=False, null=True)
    scheduled_for = models.DateTimeField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, default='cash', null=True)
    preferred_vehicle_type = models.CharField(max_length=50, default='standard', null=True)
    item_category = models.CharField(max_length=50, blank=True, null=True)
    total_duration = models.IntegerField(blank=True, null=True) 
    
    estimated_eta = models.FloatField(blank=True, null=True)
    distance_remaining = models.FloatField(blank=True, null=True)
    duration_remaining = models.IntegerField(blank=True, null=True)
    quiet_ride_requested = models.BooleanField(default=False)
    
    rider_name = models.CharField(max_length=100, blank=True, null=True)
    rider_photo = models.URLField(blank=True, null=True)
    rider_phone = models.CharField(max_length=20, blank=True, null=True)

    # 8-Stage Pricing Ledger (Screenshot 6 & 7)
    base_fare_ledger = models.FloatField(default=0.0) # Stage 1
    distance_fare_ledger = models.FloatField(default=0.0) # Stage 2 + 3 + 4
    waiting_fare_ledger = models.FloatField(default=0.0) # Stage 5
    cancellation_fee_ledger = models.FloatField(default=0.0) # Stage 6
    surge_multiplier_applied = models.FloatField(default=1.0) # Applied in Stage 4
    total_calculated_fare = models.FloatField(default=0.0) # Stage 7 (Rounding applied here)
    driver_payout_amount = models.FloatField(default=0.0) # Stage 8
    
    # Internal Tracker State (for throttling ETA recalculation)
    last_lat_update = models.FloatField(blank=True, null=True)
    last_lng_update = models.FloatField(blank=True, null=True)
    last_tracking_time = models.DateTimeField(blank=True, null=True)

    # Preferences & Carpooling (Go Parity)
    gender_preference = models.CharField(max_length=20, default='none', null=True) 
    preferred_temperature = models.CharField(max_length=50, blank=True, null=True)
    preferred_music = models.CharField(max_length=100, blank=True, null=True)
    
    is_sharing_enabled = models.BooleanField(default=False)
    max_riders = models.IntegerField(default=1)
    current_riders = models.IntegerField(default=1)
    
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, blank=True, null=True, related_name='rides')
    discount_amount = models.FloatField(default=0.0)

    dispatch_metadata = models.JSONField(default=dict, blank=True) # Tracks polled/rejected drivers
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class RideReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='receipt')
    receipt_no = models.CharField(max_length=50, unique=True)
    
    # Store finalized snapshot of the 8-stage ledger
    base_fare = models.FloatField()
    distance_fare = models.FloatField()
    waiting_fee = models.FloatField()
    cancellation_fee = models.FloatField()
    total_fare = models.FloatField()
    
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.receipt_no} for Ride {self.ride.id}"

    def __str__(self):
        return f"Ride {self.id} - {self.status}"

class FavoriteLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_locations')
    name = models.CharField(max_length=100)
    address = models.TextField()
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    type = models.CharField(max_length=20, default='home') # home, work, other
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.email}"

class Incident(models.Model):
    TYPES = (
        ('SOS', 'SOS Alert'),
        ('ACCIDENT', 'Accident'),
        ('THEFT', 'Theft'),
        ('GENERAL', 'General Incident'),
    )
    STATUS = (
        ('ACTIVE', 'Active'),
        ('RESOLVED', 'Resolved'),
        ('INVESTIGATING', 'Investigating'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='incidents')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPES, default='SOS')
    status = models.CharField(max_length=20, choices=STATUS, default='ACTIVE')
    description = models.TextField(blank=True, null=True)
    location_lat = models.FloatField(blank=True, null=True)
    location_lng = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.type} - {self.ride.id} - {self.status}"

class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_quick_message = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg from {self.sender.email} on Ride {self.ride.id}"
class Rating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_ratings')
    ratee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_ratings')
    stars = models.IntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
    rater_type = models.CharField(max_length=20) # 'rider' or 'driver'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.stars}* for {self.ratee.email} by {self.rater.email}"
class PromoCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    type = models.CharField(max_length=20) # percentage, fixed
    value = models.FloatField()
    max_discount = models.FloatField(default=0.0)
    min_ride_amount = models.FloatField(default=0.0)
    expires_at = models.DateTimeField(db_index=True)
    usage_limit = models.IntegerField(default=0) # 0 means unlimited
    usage_count = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} ({self.type})"
class RideStop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='stops')
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    stop_order = models.IntegerField(default=1) # 1, 2, 3...
    status = models.CharField(max_length=20, default='pending') # pending, arrived, completed
    arrived_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['stop_order']

    def __str__(self):
        return f"Stop {self.stop_order} for Ride {self.ride.id}"
