import uuid
from django.db import models
from profiles.models import Profile

class Vehicle(models.Model):
    STATUS_CHOICES = (
        ('offline', 'Offline'),
        ('available', 'Available'),
        ('riding', 'Riding'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    license_plate = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=50, default='go') # go, comfort, xl, exec, pragya
    
    # Document URLs
    license_url = models.URLField(max_length=1000, blank=True, null=True)
    insurance_url = models.URLField(max_length=1000, blank=True, null=True)
    roadworthy_url = models.URLField(max_length=1000, blank=True, null=True)
    video_url = models.URLField(max_length=1000, blank=True, null=True)
    insurance_expiry = models.DateField(blank=True, null=True)
    roadworthy_expiry = models.DateField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"
