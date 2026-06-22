import uuid
from django.db import models
from django.conf import settings

class Notification(models.Model):
    TYPES = (
        ('PUSH', 'Push Notification'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} to {self.user.email}: {self.title}"
class Campaign(models.Model):
    TARGET_CHOICES = (
        ('ALL', 'All Users'),
        ('DRIVER', 'Drivers Only'),
        ('PASSENGER', 'Passengers Only'),
    )
    CONDITION_CHOICES = (
        ('ALL_ACTIVE', 'All Users'),
        ('ACTIVE', 'Active Recently (Logged in < 7 days)'),
        ('INACTIVE_7_DAYS', 'Inactive (7+ days)'),
        ('INACTIVE_30_DAYS', 'Inactive (30+ days)'),
        ('HIGH_RATING', 'Highly Rated (>= 4.5)'),
        ('LOYAL', 'Loyal / Frequent Rider (>= 50 rides)'),
        ('NEW_USER', 'New User (Joined < 7 days)'),
    )
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SENDING', 'Sending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField()
    
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES, default='ALL')
    target_city = models.CharField(max_length=100, blank=True, null=True, help_text="Filter users by city. Leave blank to target all cities.")
    target_condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='ALL_ACTIVE')
    
    data_payload = models.JSONField(default=dict, blank=True, null=True, help_text="Optional JSON payload to pass with the notification (e.g. {'deep_link': '/wallet'})")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title
class FCMDevice(models.Model):
    APP_TYPES = (
        ('PASSENGER', 'Passenger App'),
        ('DRIVER', 'Driver App'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fcm_devices')
    app_type = models.CharField(max_length=20, choices=APP_TYPES, default='PASSENGER')
    registration_id = models.TextField()
    device_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.device_id}"
