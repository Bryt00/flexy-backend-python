import random
import uuid
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core_auth.models import User
from profiles.models import Profile
from rides.models import Ride, Incident
from advertising.models import AdBooking, AdSlotCapacity, AdAnalytics
from audit.models import AuditLog, FraudFlag

class Command(BaseCommand):
    help = "Seeds realistic demo data for Audit Logs, Ads Operations, and Safety Incidents/SOS"

    def handle(self, *args, **options):
        self.stdout.write("Initializing FlexyRide seed script...")

        # 1. Setup slot capacity
        AdSlotCapacity.objects.get_or_create(id=1, defaults={
            'max_ads_per_week': 6,
            'price_per_week_ghs': 200.00
        })

        # 2. Get or Create Core Users
        admin_user = User.objects.filter(role='super_admin').first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                email='admin@test.com',
                password='admin',
                role='super_admin'
            )
            self.stdout.write("Created superadmin: admin@test.com")

        driver_user = User.objects.filter(email='test@drive.com').first()
        if not driver_user:
            driver_user = User.objects.create_user(
                email='test@drive.com',
                password='password',
                role='driver'
            )
            self.stdout.write("Created driver user: test@drive.com")

        # Ensure profile exists with online status and correct details (phone, coordinates)
        driver_profile, _ = Profile.objects.defer('last_location_point').get_or_create(user=driver_user)
        driver_profile.full_name = "Kojo Boateng"
        driver_profile.phone_number = "+233 24 556 7890"
        driver_profile.last_lat = 5.6037
        driver_profile.last_lng = -0.1870
        driver_profile.is_online = True
        driver_profile.save()

        passenger_user = User.objects.filter(email='rider@test.com').first()
        if not passenger_user:
            passenger_user = User.objects.create_user(
                email='rider@test.com',
                password='password',
                role='passenger'
            )
            self.stdout.write("Created passenger user: rider@test.com")

        # 3. Create or Get Rides to associate with Incidents
        ride_1, _ = Ride.objects.defer('pickup_point', 'dropoff_point').get_or_create(
            pickup_address="Accra Mall, Spintex Rd",
            dropoff_address="Osu Oxford Street, Accra",
            defaults={
                'rider': passenger_user,
                'driver': driver_user,
                'pickup_lat': 5.6145,
                'pickup_lng': -0.1681,
                'dropoff_lat': 5.5560,
                'dropoff_lng': -0.1822,
                'status': 'in_progress',
                'fare': 45.50,
                'distance': 8.5
            }
        )

        ride_2, _ = Ride.objects.defer('pickup_point', 'dropoff_point').get_or_create(
            pickup_address="Kotoka International Airport",
            dropoff_address="East Legon, Accra",
            defaults={
                'rider': passenger_user,
                'driver': driver_user,
                'pickup_lat': 5.6053,
                'pickup_lng': -0.1668,
                'dropoff_lat': 5.6322,
                'dropoff_lng': -0.1584,
                'status': 'completed',
                'fare': 35.00,
                'distance': 5.2
            }
        )

        # 4. Seed Safety Incidents (SOS / Anomalies)
        self.stdout.write("Seeding Incidents...")
        Incident.objects.all().delete() # Start clean for demo

        incidents_data = [
            {
                'ride': ride_1,
                'reporter': passenger_user,
                'type': 'SOS',
                'status': 'ACTIVE',
                'description': 'SOS Triggered - Passenger reported driver behaving erratically near Spintex Bypass.',
                'location_lat': 5.6120,
                'location_lng': -0.1650,
            },
            {
                'ride': ride_1,
                'reporter': passenger_user,
                'type': 'SOS',
                'status': 'ACTIVE',
                'description': 'Automated Anomaly Detection: Driver location has been stuck/offline for over 15 minutes.',
                'location_lat': 5.6090,
                'location_lng': -0.1670,
            },
            {
                'ride': ride_2,
                'reporter': passenger_user,
                'type': 'SOS',
                'status': 'RESOLVED',
                'description': 'SOS Triggered - Accidental press by passenger during boarding. Resolved after support callback.',
                'location_lat': 5.6053,
                'location_lng': -0.1668,
                'resolved_at': timezone.now() - datetime.timedelta(hours=2)
            },
            {
                'ride': ride_2,
                'reporter': passenger_user,
                'type': 'SOS',
                'status': 'RESOLVED',
                'description': 'Automated Anomaly Detection: Route deviation detected on trip from Airport.',
                'location_lat': 5.6190,
                'location_lng': -0.1610,
                'resolved_at': timezone.now() - datetime.timedelta(days=1)
            }
        ]

        for inc in incidents_data:
            resolved_at = inc.pop('resolved_at', None)
            incident = Incident.objects.create(**inc)
            if resolved_at:
                incident.resolved_at = resolved_at
                incident.save()

        # 5. Seed Ads Bookings & Operations
        self.stdout.write("Seeding Ad Bookings and Analytics...")
        AdBooking.objects.all().delete() # Start clean

        today = timezone.localdate()
        recent_monday = today - datetime.timedelta(days=today.weekday())

        ads_data = [
            {
                'business_name': 'Burger King Ghana',
                'contact_email': 'marketing@burgerking.com.gh',
                'contact_phone': '+233 30 223 4455',
                'headline': 'Grab 15% Off Your Next Whopper Meal!',
                'body_text': 'Craving something flame-grilled? Book a ride to Burger King Accra Mall & show your trip receipt to get 15% discount.',
                'target_url': 'https://burgerking.com.gh',
                'status': 'LIVE',
                'payment_status': 'PAID',
                'amount': 250.00,
                'target_audience': 'ALL',
                'impressions': 12450,
                'clicks': 892
            },
            {
                'business_name': 'Vodafone Ghana',
                'contact_email': 'support@vodafone.com.gh',
                'contact_phone': '+233 20 111 2222',
                'headline': 'Infinite Data Bundles for Active Riders',
                'body_text': 'Stay connected on the move with our high-speed, non-expiring data bundles tailored for commuters and gig-workers.',
                'target_url': 'https://vodafone.com.gh',
                'status': 'LIVE',
                'payment_status': 'PAID',
                'amount': 300.00,
                'target_audience': 'PASSENGER',
                'impressions': 8200,
                'clicks': 640
            },
            {
                'business_name': 'Kempinski Hotel Gold Coast City',
                'contact_email': 'sales@kempinski.com',
                'contact_phone': '+233 24 222 3333',
                'headline': 'Weekend Getaway & Spa Treat',
                'body_text': 'Relax in absolute luxury. Enjoy premium discounts on bookings made via FlexyRide portal.',
                'target_url': 'https://kempinski.com/accra',
                'status': 'PENDING_REVIEW',
                'payment_status': 'PENDING',
                'amount': 200.00,
                'target_audience': 'ALL',
                'impressions': 0,
                'clicks': 0
            },
            {
                'business_name': 'Jumia Food GH',
                'contact_email': 'food@jumia.com.gh',
                'contact_phone': '+233 50 444 5555',
                'headline': 'Fastest Delivery in Greater Accra',
                'body_text': 'Hungry? Get delicious meals delivered straight to your doorstep from local restaurants. Enjoy free delivery today.',
                'target_url': 'https://food.jumia.com.gh',
                'status': 'APPROVED',
                'payment_status': 'PAID',
                'amount': 200.00,
                'target_audience': 'PASSENGER',
                'impressions': 0,
                'clicks': 0
            },
            {
                'business_name': 'Decathlon Accra Mall',
                'contact_email': 'decathlon@accramall.com',
                'contact_phone': '+233 24 666 7777',
                'headline': 'Back to Fitness Promo',
                'body_text': 'Get all your fitness and sporting gear at Decathlon with up to 30% off on selected equipment.',
                'target_url': 'https://decathlon.com.gh',
                'status': 'COMPLETED',
                'payment_status': 'PAID',
                'amount': 150.00,
                'target_audience': 'ALL',
                'impressions': 23410,
                'clicks': 1482
            }
        ]

        for ad in ads_data:
            impressions = ad.pop('impressions')
            clicks = ad.pop('clicks')
            
            booking = AdBooking.objects.create(
                business_name=ad['business_name'],
                contact_email=ad['contact_email'],
                contact_phone=ad['contact_phone'],
                headline=ad['headline'],
                body_text=ad['body_text'],
                target_url=ad['target_url'],
                status=ad['status'],
                payment_status=ad['payment_status'],
                amount=ad['amount'],
                target_audience=ad['target_audience'],
                week_start_date=recent_monday,
                dashboard_token=str(uuid.uuid4())[:8].upper()
            )
            
            # Update pre-created analytics
            analytics = AdAnalytics.objects.filter(ad_booking=booking).first()
            if analytics:
                analytics.impressions_a = impressions
                analytics.clicks_a = clicks
                analytics.save()

        # 6. Seed Audit Logs & Fraud Flags
        self.stdout.write("Seeding Audit Logs & Fraud Flags...")
        AuditLog.objects.all().delete()
        FraudFlag.objects.all().delete()

        audit_actions = [
            ("USER_LOGIN", "User admin@test.com logged in successfully from staff portal.", "admin@test.com"),
            ("PLATFORM_SETTING_UPDATE", "Updated dynamic matchmaking dispatch search radius to 2.5km.", "admin@test.com"),
            ("DRIVER_VERIFICATION_APPROVED", "Approved driver verification profile for Kojo Boateng (test@drive.com).", "admin@test.com"),
            ("INCIDENT_RESOLVED", "Safety SOS alert incident cba618b3 resolved by customer support.", "admin@test.com"),
            ("AD_APPROVED", "Ad booking for 'Jumia Food GH' was approved.", "admin@test.com"),
            ("PAYOUT_PROCESSED", "Processed weekly driver earnings payout block of GHS 4,500.00.", "admin@test.com"),
            ("USER_SUSPENSION", "Suspended user account malicious_rider@spam.com due to multiple fake ride requests.", "admin@test.com"),
            ("GEOFENCE_CREATED", "New service zone geofence created for Kumasi Central Business District.", "admin@test.com"),
            ("VEHICLE_UPDATED", "Updated vehicle color and status parameters for driver test@drive.com.", "admin@test.com")
        ]

        for idx, (action, details, email) in enumerate(audit_actions):
            user = User.objects.filter(email=email).first()
            AuditLog.objects.create(
                user=user,
                action=action,
                entity_id=str(uuid.uuid4())[:8],
                entity_type="SYSTEM_ACTION" if "SYSTEM" in action else "USER_MANAGEMENT",
                details={"message": details, "index": idx},
                ip_address=f"192.168.1.{random.randint(10, 254)}"
            )

        fraud_flags_data = [
            {
                'type': 'LOCATION_SPOOFING',
                'severity': 'HIGH',
                'user': driver_user,
                'details': 'Driver GPS coordinate jumps suggest developer mock location or root bypass tools active.',
                'status': 'FLAGGED'
            },
            {
                'type': 'UNUSUAL_FARE',
                'severity': 'MEDIUM',
                'user': passenger_user,
                'details': 'Rider transaction attempted multiple short-distance high-amount trip cards.',
                'status': 'FLAGGED'
            }
        ]

        for flag in fraud_flags_data:
            FraudFlag.objects.create(**flag)

        self.stdout.write(self.style.SUCCESS("Demo database successfully populated!"))
