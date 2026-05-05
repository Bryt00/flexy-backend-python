"""Seed Service Categories for the marketing website."""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from website.models import ServiceCategory

services = [
    {
        'name': 'Flexy Go',
        'description': 'Your go-to option for quick, budget-friendly trips around the city. Whether it is your daily commute, a quick errand, or a trip to the market — Flexy Go gets you there fast without breaking the bank. Compact, reliable, and always just a tap away.',
        'order': 1,
    },
    {
        'name': 'Flexy Comfort',
        'description': 'Upgrade your journey with spacious sedans, climate-controlled cabins, and top-rated drivers. Flexy Comfort is perfect for business meetings, airport transfers, or any occasion where first impressions matter. Premium comfort at an accessible price.',
        'order': 2,
    },
    {
        'name': 'Flexy XL',
        'description': 'Travelling with family, friends, or extra luggage? Flexy XL offers spacious SUVs and minivans that seat up to 6 passengers comfortably. Ideal for group outings, weekend getaways, and airport runs with heavy bags.',
        'order': 3,
    },
    {
        'name': 'Flexy Exec',
        'description': 'Arrive like a VIP. Flexy Exec pairs you with luxury vehicles and professionally trained chauffeurs for a first-class travel experience. From corporate events to special celebrations, this is the premium tier for those who demand the very best.',
        'order': 4,
    },
    {
        'name': 'Flexy Pragya',
        'description': "Ghana's favourite way to navigate busy streets. Flexy Pragya connects you with licensed motorbike riders for the fastest point-to-point trips in the city. Perfect for short distances, tight schedules, and peak-hour traffic.",
        'order': 5,
    },
]

for s in services:
    obj, created = ServiceCategory.objects.update_or_create(
        name=s['name'],
        defaults={'description': s['description'], 'order': s['order'], 'is_active': True}
    )
    status = 'Created' if created else 'Updated'
    print(f"{status}: {obj.name}")

print("\nDone! All service categories seeded.")
