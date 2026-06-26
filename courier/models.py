import uuid
from django.db import models
from django.conf import settings
from profiles.models import Profile
from core_settings.models import DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('AT_PICKUP', 'At Pickup'),
        ('PACKAGE_COLLECTED', 'Package Collected'),
        ('EN_ROUTE_TO_DROPOFF', 'En Route to Dropoff'),
        ('ARRIVED_AT_DROPOFF', 'Arrived at Dropoff'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passenger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deliveries_requested')
    driver = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='courier_deliveries')
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    item_category = models.ForeignKey(DeliveryCategory, on_delete=models.SET_NULL, null=True, blank=True)
    weight_tier = models.ForeignKey(DeliveryWeightTier, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_type = models.ForeignKey(DeliveryVehicleType, on_delete=models.SET_NULL, null=True, blank=True)
    weight = models.FloatField(blank=True, null=True)
    
    # Location Information
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    pickup_address = models.TextField(blank=True, null=True)
    
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()
    dropoff_address = models.TextField(blank=True, null=True)
    
    # Package Information
    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=50)
    delivery_notes = models.TextField(blank=True, null=True)
    proof_photo_url = models.URLField(blank=True, null=True)
    
    # Pricing
    estimated_fare = models.FloatField(default=0.0)
    base_fare = models.FloatField(default=0.0)
    distance_fee = models.FloatField(default=0.0)
    final_fare = models.FloatField(blank=True, null=True)
    promo_code_string = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.FloatField(default=0.0)
    surge_multiplier_applied = models.FloatField(default=1.0)
    
    distance = models.FloatField(default=0.0)
    estimated_eta = models.FloatField(default=0.0)
    
    metadata = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery {self.id} - {self.status}"

class DeliveryProof(models.Model):
    PROOF_TYPES = (
        ('PICKUP', 'Pickup Proof'),
        ('DROPOFF', 'Dropoff Proof'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='proofs')
    proof_type = models.CharField(max_length=20, choices=PROOF_TYPES)
    image_url = models.URLField(blank=True, null=True)
    signature_base64 = models.TextField(blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_proof_type_display()} for Delivery {self.delivery.id}"
