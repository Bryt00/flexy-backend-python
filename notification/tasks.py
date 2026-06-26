from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import datetime
from .models import Campaign
from core_auth.models import User
from .utils import send_notification
import logging

logger = logging.getLogger(__name__)

def get_campaign_users(campaign):
    """
    Helper to fetch the queryset of users for a given campaign 
    based on its target_audience, target_city, and target_condition.
    """
    if campaign.target_audience == 'ALL':
        users = User.objects.filter(is_active=True)
    elif campaign.target_audience == 'DRIVER':
        users = User.objects.filter(is_active=True, role='driver')
    else: # PASSENGER
        users = User.objects.filter(is_active=True, role='passenger')

    if campaign.target_city:
        users = users.filter(profile__city__icontains=campaign.target_city)

    now = timezone.now()
    if campaign.target_condition == 'ACTIVE':
        cutoff = now - datetime.timedelta(days=7)
        users = users.filter(last_login__gte=cutoff)
    elif campaign.target_condition == 'INACTIVE_7_DAYS':
        cutoff = now - datetime.timedelta(days=7)
        users = users.filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
    elif campaign.target_condition == 'INACTIVE_30_DAYS':
        cutoff = now - datetime.timedelta(days=30)
        users = users.filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
    elif campaign.target_condition == 'HIGH_RATING':
        users = users.filter(profile__rating__gte=4.5)
    elif campaign.target_condition == 'LOYAL':
        users = users.filter(profile__total_rides__gte=50)
    elif campaign.target_condition == 'NEW_USER':
        cutoff = now - datetime.timedelta(days=7)
        users = users.filter(created_at__gte=cutoff)

    return users

@shared_task
def send_fcm_push_task(user_id, title, message, data=None, app_type=None):
    """
    Background task to send FCM push via Celery/RabbitMQ
    """
    try:
        from django.conf import settings
        from django.utils.module_loading import import_string
        
        provider_class = import_string(settings.ACTIVE_PUSH_PROVIDER)
        provider = provider_class()
        
        android_channel_id = data.pop('android_channel_id', None) if data else None
        android_sound = data.pop('android_sound', None) if data else None
        ios_sound = data.pop('ios_sound', None) if data else None

        provider.send_push(
            user_id=user_id, 
            title=title, 
            message=message, 
            data=data,
            android_channel_id=android_channel_id,
            android_sound=android_sound,
            ios_sound=ios_sound,
            app_type=app_type
        )
    except Exception as e:
        logger.error(f"Failed to execute FCM push task: {e}")

@shared_task
def broadcast_campaign_push_task(campaign_id):
    """
    Background task to broadcast a campaign via Push Notifications.
    """
    from django.db import close_old_connections
    close_old_connections()
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        campaign.status = 'SENDING'
        campaign.save()

        # Fetch targeted users
        users = get_campaign_users(campaign)

        count = 0
        for user in users:
            try:
                send_notification(user, campaign.title, campaign.body, extra_data=campaign.data_payload)
                count += 1
            except Exception as e:
                logger.error(f"Failed to send campaign push to {user.email}: {e}")

        campaign.status = 'SENT'
        campaign.sent_at = timezone.now()
        campaign.save()
        logger.info(f"Campaign push '{campaign.title}' successfully sent to {count} users.")

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found.")
    except Exception as e:
        logger.error(f"Error sending campaign push {campaign_id}: {e}")
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = 'FAILED'
            campaign.save()
        except:
            pass
    finally:
        close_old_connections()

@shared_task
def broadcast_campaign_email_task(campaign_id):
    """
    Background task to broadcast a campaign via Bulk Email.
    """
    from django.db import close_old_connections
    from integrations.email_service import EmailService
    close_old_connections()
    try:
        campaign = Campaign.objects.get(id=campaign_id)

        # Fetch targeted users
        users = get_campaign_users(campaign)

        EmailService.send_bulk_campaign_email(campaign, users)

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found.")
    except Exception as e:
        logger.error(f"Error sending campaign email {campaign_id}: {e}")
    finally:
        close_old_connections()

def was_notified_recently(user, title, days_limit):
    """
    Checks if a notification with the given title was already sent to the user
    within the last days_limit days.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Notification
    cutoff = timezone.now() - timedelta(days=days_limit)
    return Notification.objects.filter(
        user=user,
        title=title,
        created_at__gte=cutoff
    ).exists()

@shared_task
def check_document_expirations():
    """
    Daily task to scan driver verifications and vehicle records for expiring
    documents in 1, 7, or dynamic threshold days, and dispatch push notifications.
    Uses range checks to ensure no drivers are missed if the task was not executed
    on the exact day, while avoiding duplicate notifications.
    """
    import datetime
    from django.utils import timezone
    from profiles.models import DriverVerification
    from vehicles.models import Vehicle
    from notification.utils import send_notification
    from core_settings.models import SiteSetting
    from django.conf import settings
    import logging

    logger = logging.getLogger(__name__)
    today = timezone.localdate()

    threshold_days = 7
    try:
        setting = SiteSetting.objects.filter(key="DOCUMENT_RENEWAL_THRESHOLD_DAYS").first()
        if setting and setting.value.strip().isdigit():
            threshold_days = int(setting.value.strip())
        else:
            threshold_days = getattr(settings, 'DOCUMENT_RENEWAL_THRESHOLD_DAYS', 7)
    except Exception:
        threshold_days = getattr(settings, 'DOCUMENT_RENEWAL_THRESHOLD_DAYS', 7)

    thresholds = sorted(list(set([1, 7, threshold_days])))

    logger.info(f"Starting check_document_expirations task with thresholds {thresholds}...")

    for days in thresholds:
        target_date = today + datetime.timedelta(days=days)
        label = "TOMORROW" if days == 1 else f"in {days} days"

        # 1. Driver Verification Documents (License & ID Card)
        # We only check drivers whose status is VERIFIED
        verifications = DriverVerification.objects.filter(is_verified=True)
        
        # License Expiration
        license_expiring = verifications.filter(
            license_expiry_date__lte=target_date,
            license_expiry_date__gte=today
        )
        for ver in license_expiring:
            title = "⚠️ Driver's License Expiring Soon"
            if not was_notified_recently(ver.driver.user, title, days):
                try:
                    body = f"Your driver's license expires {label}. Please update it to avoid service interruption."
                    send_notification(ver.driver.user, title, body, type='PUSH')
                    logger.info(f"Sent license expiry notification ({days} days) to user {ver.driver.user.email}")
                except Exception as e:
                    logger.error(f"Error notifying license expiry for {ver.driver}: {e}")

        # ID Card Expiration
        id_card_expiring = verifications.filter(
            id_card_expiry_date__lte=target_date,
            id_card_expiry_date__gte=today
        )
        for ver in id_card_expiring:
            title = "⚠️ ID Card Expiring Soon"
            if not was_notified_recently(ver.driver.user, title, days):
                try:
                    body = f"Your identity document expires {label}. Please update it to avoid service interruption."
                    send_notification(ver.driver.user, title, body, type='PUSH')
                    logger.info(f"Sent ID card expiry notification ({days} days) to user {ver.driver.user.email}")
                except Exception as e:
                    logger.error(f"Error notifying ID card expiry for {ver.driver}: {e}")

        # 2. Vehicle Documents (Insurance & Roadworthy)
        vehicles = Vehicle.objects.filter(is_verified=True, is_active=True)

        # Insurance Expiration
        insurance_expiring = vehicles.filter(
            insurance_expiry__lte=target_date,
            insurance_expiry__gte=today
        )
        for veh in insurance_expiring:
            title = "⚠️ Vehicle Insurance Expiring Soon"
            if not was_notified_recently(veh.driver.user, title, days):
                try:
                    body = f"The insurance for your vehicle ({veh.make} {veh.model}) expires {label}. Please upload your new document to stay active."
                    send_notification(veh.driver.user, title, body, type='PUSH')
                    logger.info(f"Sent insurance expiry notification ({days} days) to user {veh.driver.user.email}")
                except Exception as e:
                    logger.error(f"Error notifying insurance expiry for vehicle {veh}: {e}")

        # Roadworthy Expiration
        roadworthy_expiring = vehicles.filter(
            roadworthy_expiry__lte=target_date,
            roadworthy_expiry__gte=today
        )
        for veh in roadworthy_expiring:
            title = "⚠️ Roadworthy Certificate Expiring Soon"
            if not was_notified_recently(veh.driver.user, title, days):
                try:
                    body = f"The roadworthy certificate for your vehicle ({veh.make} {veh.model}) expires {label}. Please upload your new certificate to stay active."
                    send_notification(veh.driver.user, title, body, type='PUSH')
                    logger.info(f"Sent roadworthy expiry notification ({days} days) to user {veh.driver.user.email}")
                except Exception as e:
                    logger.error(f"Error notifying roadworthy expiry for vehicle {veh}: {e}")

@shared_task
def send_driver_birthday_pushes():
    """
    Daily task to check for drivers whose birthday is today, and send them a birthday push notification.
    """
    import datetime
    from django.utils import timezone
    from profiles.models import Profile
    from notification.utils import send_notification
    import logging

    logger = logging.getLogger(__name__)
    today = timezone.localdate()

    birthday_profiles = Profile.objects.filter(
        user__role='driver',
        user__is_active=True,
        date_of_birth__month=today.month,
        date_of_birth__day=today.day
    )

    count = 0
    from notification.models import Notification
    from core_settings.models import SiteSetting
    
    title_setting = SiteSetting.objects.filter(key="BIRTHDAY_PUSH_TITLE").first()
    body_setting = SiteSetting.objects.filter(key="BIRTHDAY_PUSH_BODY").first()
    
    for profile in birthday_profiles:
        try:
            first_name = profile.user.first_name or "Driver"
            
            title = title_setting.value if title_setting else "🎉 Happy Birthday from FlexyRide!"
            
            if Notification.objects.filter(user=profile.user, title=title, created_at__year=today.year).exists():
                continue
                
            body_template = body_setting.value if body_setting else "Happy Birthday, {first_name}! Wishing you a fantastic day and many happy rides ahead."
            body = body_template.replace("{first_name}", first_name)
            
            send_notification(profile.user, title, body, type='PUSH')
            count += 1
            logger.info(f"Sent birthday push to {profile.user.email}")
        except Exception as e:
            logger.error(f"Error sending birthday push to {profile.user.email}: {e}")
            
    logger.info(f"Birthday push task completed. Sent {count} pushes.")
