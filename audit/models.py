import uuid
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    entity_type = models.CharField(max_length=100, blank=True, null=True)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} on {self.entity_type}"

class FraudFlag(models.Model):
    TYPES = (
        ('LOCATION_SPOOFING', 'Location Spoofing'),
        ('UNUSUAL_FARE', 'Unusual Fare'),
        ('MULTIPLE_ACCOUNTS', 'Multiple Accounts'),
        ('FAST_MOVEMENT', 'Fast Movement'),
    )
    SEVERITY = (
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    )
    STATUS = (
        ('FLAGGED', 'Flagged'),
        ('RESOLVED', 'Resolved'),
        ('IGNORED', 'Ignored'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, choices=TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fraud_flags')
    details = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='FLAGGED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fraud: {self.type} - {self.user.email}"
