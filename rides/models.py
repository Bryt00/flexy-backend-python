import uuid
from django.db import models
from django.conf import settings
from profiles.models import Profile

class Ride(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    
    service_type = models.CharField(max_length=50, blank=True, null=True)
    pickup_location = models.TextField(blank=True, null=True)
    dropoff_location = models.TextField(blank=True, null=True)
    
    pickup_lat = models.FloatField(blank=True, null=True)
    pickup_lng = models.FloatField(blank=True, null=True)
    
    dropoff_lat = models.FloatField(blank=True, null=True)
    dropoff_lng = models.FloatField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    fare = models.FloatField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride {self.id} - {self.status}"

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
