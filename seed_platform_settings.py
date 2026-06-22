import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from core_settings.models import SiteSetting, PricingRule
from website.models import City

def seed_platform_settings():
    print("Seeding Site Settings...")
    
    # 1. Seed Site Settings
    settings_data = [
        {
            'key': 'maps_country_restriction',
            'value': 'gh',
            'description': 'Country code for Google Places search geofencing (e.g. gh, ng, gb)'
        },
        {
            'key': 'contact_email',
            'value': 'support@flexyride.com',
            'description': 'Contact email shown on marketing website'
        },
        {
            'key': 'contact_phone',
            'value': '+233 24 000 0000',
            'description': 'Contact phone shown on marketing website'
        },
        {
            'key': 'DOCUMENT_RENEWAL_THRESHOLD_DAYS',
            'value': '30',
            'description': 'Number of days before doc expiry to alert drivers'
        },
        {
            'key': 'support_email',
            'value': 'sos@flexyride.com',
            'description': 'Support email for SOS/safety escalations'
        },
        {
            'key': 'support_phone',
            'value': '+233 24 111 1111',
            'description': 'Support phone for SOS/safety escalations'
        },
        {
            'key': 'surge_enabled',
            'value': 'true',
            'description': 'Global toggle for real-time demand-based pricing'
        }
    ]

    for data in settings_data:
        setting, created = SiteSetting.objects.get_or_create(
            key=data['key'],
            defaults={'value': data['value'], 'description': data['description']}
        )
        if created:
            print(f"Created SiteSetting: {data['key']} = '{data['value']}'")
        else:
            print(f"SiteSetting '{data['key']}' already exists.")

    print("\nSeeding Cities...")
    # 2. Seed Cities
    cities_data = [
        {
            'name': 'Accra',
            'region': 'Greater Accra',
            'is_active': True,
            'driver_count': 1250,
            'latitude': 5.6037,
            'longitude': -0.1870,
            'cover_image_url': 'https://images.unsplash.com/photo-1598913929424-656360492160?q=80&w=800'
        },
        {
            'name': 'Kumasi',
            'region': 'Ashanti',
            'is_active': True,
            'driver_count': 840,
            'latitude': 6.6666,
            'longitude': -1.6163,
            'cover_image_url': 'https://images.unsplash.com/photo-1580674239581-4d48f7c7ef4e?q=80&w=800'
        }
    ]

    cities = []
    for city_info in cities_data:
        city, created = City.objects.get_or_create(
            name=city_info['name'],
            region=city_info['region'],
            defaults={
                'is_active': city_info['is_active'],
                'driver_count': city_info['driver_count'],
                'latitude': city_info['latitude'],
                'longitude': city_info['longitude'],
                'cover_image_url': city_info['cover_image_url']
            }
        )
        cities.append(city)
        if created:
            print(f"Created City: {city.name}")
        else:
            print(f"City '{city.name}' already exists.")

    print("\nSeeding Pricing Rules...")
    # 3. Seed Pricing Rules (including Global Default and City-Specific)
    
    # Global Default (city=None)
    global_rule, created = PricingRule.objects.get_or_create(
        city=None,
        defaults={
            'base_fare': 15.0,
            'per_km_rate': 5.0,
            'per_minute_rate': 1.0,
            'surge_multiplier': 1.0,
            'enable_weather_surge': True,
            'enable_traffic_surge': True,
            'max_weather_surge': 1.5,
            'max_traffic_surge': 1.5,
            'is_active': True
        }
    )
    if created:
        print("Created Global Default Pricing Rule")
    else:
        print("Global Default Pricing Rule already exists.")

    # Accra Rates
    accra = next((c for c in cities if c.name == 'Accra'), None)
    if accra:
        accra_rule, created = PricingRule.objects.get_or_create(
            city=accra,
            defaults={
                'base_fare': 18.0,
                'per_km_rate': 6.0,
                'per_minute_rate': 1.2,
                'surge_multiplier': 1.0,
                'enable_weather_surge': True,
                'enable_traffic_surge': True,
                'max_weather_surge': 1.8,
                'max_traffic_surge': 1.8,
                'is_active': True
            }
        )
        if created:
            print("Created Accra Pricing Rule")
        else:
            print("Accra Pricing Rule already exists.")

    # Kumasi Rates
    kumasi = next((c for c in cities if c.name == 'Kumasi'), None)
    if kumasi:
        kumasi_rule, created = PricingRule.objects.get_or_create(
            city=kumasi,
            defaults={
                'base_fare': 16.0,
                'per_km_rate': 5.5,
                'per_minute_rate': 1.0,
                'surge_multiplier': 1.0,
                'enable_weather_surge': True,
                'enable_traffic_surge': False,
                'max_weather_surge': 1.5,
                'max_traffic_surge': 1.2,
                'is_active': True
            }
        )
        if created:
            print("Created Kumasi Pricing Rule")
        else:
            print("Kumasi Pricing Rule already exists.")

    print("\nSeeding complete!")

if __name__ == '__main__':
    seed_platform_settings()
