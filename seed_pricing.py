import os
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from core_settings.models import VehicleCategory, DistanceTier

def seed_pricing():
    print("Seeding Pricing Data...")
    
    # 1. Clear existing data to avoid duplicates during dev
    print("Cleaning old categories and tiers...")
    VehicleCategory.objects.all().delete()
    DistanceTier.objects.all().delete()

    # 2. Add Vehicle Categories (from PDF)
    categories = [
        {'slug': 'go', 'display_name': 'Go', 'base_fare': 18.0, 'multiplier': 1.00},
        {'slug': 'comfort', 'display_name': 'Comfort', 'base_fare': 22.0, 'multiplier': 1.25},
        {'slug': 'exec', 'display_name': 'Exec', 'base_fare': 30.0, 'multiplier': 2.00},
        {'slug': 'xl', 'display_name': 'XL', 'base_fare': 26.0, 'multiplier': 1.50},
        {'slug': 'pragya', 'display_name': 'Pragya', 'base_fare': 10.0, 'multiplier': 0.60},
        {'slug': 'motorbike', 'display_name': 'Motorbike', 'base_fare': 8.0, 'multiplier': 0.50},
    ]

    for cat in categories:
        VehicleCategory.objects.create(**cat)
        print(f"Created category: {cat['display_name']}")

    # 3. Add Distance Tiers (from PDF)
    # Tier 1: 0-5 km @ 6.0
    # Tier 2: 5-11 km @ 5.0
    # Tier 3: 11-17 km @ 4.5
    # Tier 4: 17+ km @ 4.0
    
    tiers = [
        {'name': 'Short Distance', 'min_km': 0.0, 'max_km': 5.0, 'rate_per_km': 6.0},
        {'name': 'Medium Distance', 'min_km': 5.0, 'max_km': 11.0, 'rate_per_km': 5.0},
        {'name': 'Long Distance', 'min_km': 11.0, 'max_km': 17.0, 'rate_per_km': 4.5},
        {'name': 'Extra Long Distance', 'min_km': 17.0, 'max_km': 9999.0, 'rate_per_km': 4.0},
    ]

    for tier in tiers:
        DistanceTier.objects.create(**tier)
        print(f"Created tier: {tier['name']} ({tier['rate_per_km']} GHS/km)")

    print("Seeding complete!")

if __name__ == "__main__":
    seed_pricing()
