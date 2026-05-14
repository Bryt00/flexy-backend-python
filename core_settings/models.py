from django.db import models
import uuid

class SiteSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key

class LegalDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    version = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (v{self.version})"

class PricingRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey('website.City', on_delete=models.CASCADE, related_name='pricing_rules', null=True, blank=True)
    base_fare = models.FloatField(default=0.0)
    per_km_rate = models.FloatField(default=0.0)
    per_minute_rate = models.FloatField(default=0.0)
    surge_multiplier = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pricing for {self.city}"

class VehicleCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=50, unique=True, help_text="Short name for code (e.g. 'standard', 'pragya', 'comfort')")
    display_name = models.CharField(max_length=100, help_text="Human readable name (e.g. 'Go', 'Pragya')")
    base_fare = models.FloatField(default=0.0)
    multiplier = models.FloatField(default=1.0, help_text="Fare multiplier for this category")
    image = models.ImageField(upload_to='vehicle_categories/', blank=True, null=True, help_text="Upload an icon for this vehicle type (PNG recommended)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Vehicle Categories"

    def __str__(self):
        return f"{self.display_name} ({self.slug})"

class DistanceTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Tier", help_text="e.g. 'Short Distance', 'Long Distance'")
    min_km = models.FloatField(default=0.0)
    max_km = models.FloatField(default=0.0, help_text="Use a very large number like 9999 for the last tier")
    rate_per_km = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['min_km']

    def __str__(self):
        return f"{self.name}: {self.min_km}km - {self.max_km}km @ {self.rate_per_km}/km"
