import uuid
from django.db import models
from django.conf import settings

class PromoCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.FloatField(blank=True, null=True)
    discount_amount = models.FloatField(blank=True, null=True)
    max_discount = models.FloatField(blank=True, null=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(default=100)
    times_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

class Campaign(models.Model):
    STATUS = (
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    target_url = models.URLField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS, default='ACTIVE')
    
    start_date = models.DateTimeField(auto_now_add=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    
    target_audience = models.CharField(max_length=100, default='all')
    message_payload = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == 'ACTIVE'
