from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from profiles.models import Profile, DriverVerification
from vehicles.models import Vehicle

User = get_user_model()

class Command(BaseCommand):
    help = 'Force verifies a driver and their vehicles'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the driver to verify')

    def handle(self, *args, **options):
        email = options['email']
        user = User.objects.filter(email=email).first()
        
        if not user:
            self.stdout.write(self.style.ERROR(f"User with email {email} not found"))
            return

        profile, _ = Profile.objects.get_or_create(user=user)
        verification, _ = DriverVerification.objects.get_or_create(driver=profile)
        
        verification.status = 'VERIFIED'
        verification.is_verified = True
        verification.save()
        
        verification.approve() # This also syncs vehicles
        
        # Ensure profile has a location for Redis
        if not profile.last_lat:
            profile.last_lat = 5.6037
            profile.last_lng = -0.1870
            profile.save()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully verified {email} and their vehicles."))
