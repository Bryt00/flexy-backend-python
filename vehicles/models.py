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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"
