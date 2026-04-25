import os
import django
import datetime
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from advertising.models import AdBooking, AdSlotCapacity

def seed_ads():
    print("Seeding advertisements...")
    
    # Ensure capacity exists
    AdSlotCapacity.objects.get_or_create(id=1)
    
    # Get recent Monday
    today = timezone.localdate()
    days_behind = today.weekday() # Monday is 0
    recent_monday = today - datetime.timedelta(days=days_behind)
    
    # Ad data
    ads = [
        {
            'business_name': 'Burger King GH',
            'headline': 'The Whopper is Here!',
            'body_text': 'Enjoy the flame-grilled taste of the Whopper. Order now and get 10% off your first ride to any branch.',
            'image': 'ads/ad_burger.png',
            'target_url': 'https://burgerking.com.gh',
        },
        {
            'business_name': 'TechHub Accra',
            'headline': 'Next-Gen Coworking',
            'body_text': 'Need a quiet place to work? TechHub offers high-speed internet and premium coffee. First day is free!',
            'image': 'ads/ad_tech.png',
            'target_url': 'https://techhub.com.gh',
        },
        {
            'business_name': 'Vogue Essentials',
            'headline': 'Summer Collection Out!',
            'body_text': 'Upgrade your wardrobe with our new summer collection. Visit our store at Osu for exclusive deals.',
            'image': 'ads/ad_fashion.png',
            'target_url': 'https://vogue essentials.gh',
        }
    ]
    
    for ad_data in ads:
        ad, created = AdBooking.objects.get_or_create(
            headline=ad_data['headline'],
            defaults={
                'business_name': ad_data['business_name'],
                'body_text': ad_data['body_text'],
                'image': ad_data['image'],
                'target_url': ad_data['target_url'],
                'week_start_date': recent_monday,
                'status': 'LIVE',
                'payment_status': 'PAID',
                'amount': 150.00
            }
        )
        if created:
            print(f"Created ad: {ad.headline}")
        else:
            # Update to LIVE if it exists
            ad.status = 'LIVE'
            ad.week_start_date = recent_monday
            ad.save()
            print(f"Updated ad: {ad.headline}")

if __name__ == "__main__":
    seed_ads()
    print("Done!")
