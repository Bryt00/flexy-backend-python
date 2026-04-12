from django.db import models
from django.conf import settings
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture_url = models.TextField(blank=True, null=True)
    rating = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.email

class DriverVerification(models.Model):
    driver = models.OneToOneField(Profile, on_delete=models.CASCADE, primary_key=True, related_name='verification')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    license_image_url = models.TextField(blank=True, null=True)
    id_card_image_url = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Verification for {self.driver.user.email}"
