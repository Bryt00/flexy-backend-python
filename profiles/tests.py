import pytest
from django.utils import timezone
from core_auth.models import User
from profiles.models import Profile, DriverVerification
from vehicles.models import Vehicle
from subscriptions.models import DriverSubscription

@pytest.mark.django_db
def test_driver_verification_save_sync():
    # 1. Create a test user and profile
    user = User.objects.create_user(email='driver@example.com', password='password123', role='driver')
    profile = Profile.objects.create(user=user, full_name='Test Driver')
    
    # Create a vehicle linked to profile
    vehicle = Vehicle.objects.create(
        driver=profile,
        license_plate='TEST-123',
        make='Toyota',
        model='Vitz',
        year=2020,
        color='Red',
        type='go',
        is_active=False,
        is_verified=False
    )
    
    # 2. Save DriverVerification with is_verified=False
    verification = DriverVerification.objects.create(
        driver=profile,
        license_number='LIC-12345',
        status='PENDING',
        is_verified=False
    )
    
    # Verify no subscription and vehicle is not active
    assert not DriverSubscription.objects.filter(profile=profile).exists()
    vehicle.refresh_from_db()
    assert not vehicle.is_verified
    assert not vehicle.is_active

    # 3. Modify DriverVerification is_verified=True and save
    verification.is_verified = True
    verification.status = 'VERIFIED'
    verification.save()

    # Verify DriverSubscription is created with 14-day free trial
    assert DriverSubscription.objects.filter(profile=profile).exists()
    sub = DriverSubscription.objects.get(profile=profile)
    assert sub.is_trial_used
    assert sub.is_in_trial
    assert sub.trial_days_remaining == 14
    
    # Verify vehicle is synced and activated
    vehicle.refresh_from_db()
    assert vehicle.is_verified
    assert vehicle.is_active

@pytest.mark.django_db
def test_driver_verification_approve_method():
    # 1. Create a test user, profile, and vehicle
    user = User.objects.create_user(email='driver2@example.com', password='password123', role='driver')
    profile = Profile.objects.create(user=user, full_name='Test Driver 2')
    
    vehicle = Vehicle.objects.create(
        driver=profile,
        license_plate='TEST-456',
        make='Toyota',
        model='Yaris',
        year=2021,
        color='Blue',
        type='comfort',
        is_active=False,
        is_verified=False
    )
    
    verification = DriverVerification.objects.create(
        driver=profile,
        license_number='LIC-67890',
        status='PENDING',
        is_verified=False
    )
    
    # Mock send_notification and EmailService to avoid errors / network calls
    from unittest.mock import patch
    with patch('profiles.models.send_notification') as mock_notify, \
         patch('profiles.models.EmailService.send_verification_status_email') as mock_email:
        
        # Call approve()
        verification.approve()
        
        # Verify status and attributes
        assert verification.status == 'VERIFIED'
        assert verification.is_verified
        assert verification.verified_at is not None
        
        # Verify subscription and vehicle sync
        assert DriverSubscription.objects.filter(profile=profile).exists()
        sub = DriverSubscription.objects.get(profile=profile)
        assert sub.is_trial_used
        assert sub.is_in_trial
        
        vehicle.refresh_from_db()
        assert vehicle.is_verified
        assert vehicle.is_active
        
        # Verify notifications called
        mock_notify.assert_called_once()
        mock_email.assert_called_once()
