from django.db import models
import uuid

class SiteSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def field_type(self):
        val = self.value.strip().lower()
        key_lower = self.key.lower()
        if val in ['true', 'false']:
            return 'boolean'
        elif 'email' in key_lower:
            return 'email'
        elif 'phone' in key_lower:
            return 'phone'
        elif val.isdigit():
            return 'number'
        else:
            return 'text'

    @property
    def is_boolean(self):
        return self.field_type == 'boolean'

    @property
    def is_email(self):
        return self.field_type == 'email'

    @property
    def is_phone(self):
        return self.field_type == 'phone'

    @property
    def is_number(self):
        return self.field_type == 'number'

    @property
    def is_text(self):
        return self.field_type == 'text'
        
    @property
    def boolean_value(self):
        return self.value.strip().lower() == 'true'

    def __str__(self):
        return self.key

    @classmethod
    def get_cached_value(cls, key, default=None):
        from django.core.cache import cache
        cache_key = f"site_setting_{key}"
        val = cache.get(cache_key)
        if val is None:
            setting = cls.objects.filter(key=key).first()
            val = setting.value if setting else default
            cache.set(cache_key, val, timeout=900)
        return val

    def save(self, *args, **kwargs):
        from django.core.cache import cache
        cache_key = f"site_setting_{self.key}"
        cache.delete(cache_key)
        super().save(*args, **kwargs)

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
    
    # Environmental Surge Toggles
    enable_weather_surge = models.BooleanField(default=True, help_text="Automatically increase prices during adverse weather")
    enable_traffic_surge = models.BooleanField(default=True, help_text="Automatically increase prices during severe traffic delays")
    max_weather_surge = models.FloatField(default=1.5, help_text="Maximum multiplier for severe weather (e.g. 1.5x)")
    max_traffic_surge = models.FloatField(default=1.5, help_text="Maximum multiplier for heavy traffic (e.g. 1.5x)")
    
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

class DeliveryCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. 'Documents', 'Food', 'Electronics'")
    markup_percentage = models.FloatField(default=0.0, help_text="Percentage markup (e.g. 10.0 for 10% extra)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Delivery Categories"

    def __str__(self):
        return self.name

class DeliveryWeightTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. 'Light (< 5kg)'")
    min_weight = models.FloatField(default=0.0)
    max_weight = models.FloatField(default=0.0, help_text="Use a high number like 9999 for the highest tier")
    markup_percentage = models.FloatField(default=0.0, help_text="Percentage markup (e.g. 20.0 for 20% extra)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['min_weight']

    def __str__(self):
        return f"{self.name} ({self.min_weight}kg - {self.max_weight}kg)"

class DeliveryVehicleType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. 'Motorbike', 'Truck', 'Van'")
    base_fare = models.FloatField(default=0.0, help_text="Base fare for this vehicle type")
    per_km_rate = models.FloatField(default=0.0, help_text="Rate per km for this vehicle type")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
