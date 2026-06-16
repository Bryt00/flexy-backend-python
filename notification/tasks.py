from celery import shared_task
from django.utils import timezone
from .models import Campaign
from core_auth.models import User
from .utils import send_notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_fcm_push_task(user_id, title, message, data=None):
    """
    Background task to send FCM push via Celery/RabbitMQ
    """
    try:
        from django.conf import settings
        from django.utils.module_loading import import_string
        
        provider_class = import_string(settings.ACTIVE_PUSH_PROVIDER)
        provider = provider_class()
        provider.send_push(user_id=user_id, title=title, message=message, data=data)
    except Exception as e:
        logger.error(f"Failed to execute FCM push task: {e}")

@shared_task
def send_campaign_task(campaign_id):
    """
    Background task to broadcast a marketing message to a target audience.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        campaign.status = 'SENDING'
        campaign.save()

        # Fetch targeted users
        if campaign.target_audience == 'ALL':
            users = User.objects.filter(is_active=True)
        elif campaign.target_audience == 'DRIVER':
            users = User.objects.filter(is_active=True, role='driver')
        else: # PASSENGER
            users = User.objects.filter(is_active=True, role='passenger')

        count = 0
        for user in users:
            try:
                send_notification(user, campaign.title, campaign.body)
                count += 1
            except Exception as e:
                logger.error(f"Failed to send campaign notification to {user.email}: {e}")

        campaign.status = 'SENT'
        campaign.sent_at = timezone.now()
        campaign.save()
        logger.info(f"Campaign '{campaign.title}' successfully sent to {count} users.")

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found.")
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {e}")
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = 'FAILED'
            campaign.save()
        except:
            pass

@shared_task
def check_document_expirations():
    """
    Daily task to scan driver verifications and vehicle records for expiring
    documents in 1, 7, or dynamic threshold days, and dispatch push notifications.
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
        license_expiring = verifications.filter(license_expiry_date=target_date)
        for ver in license_expiring:
            try:
                title = "⚠️ Driver's License Expiring Soon"
                body = f"Your driver's license expires {label}. Please update it to avoid service interruption."
                send_notification(ver.driver.user, title, body, type='PUSH')
                logger.info(f"Sent license expiry notification ({days} days) to user {ver.driver.user.email}")
            except Exception as e:
                logger.error(f"Error notifying license expiry for {ver.driver}: {e}")

        # ID Card Expiration
        id_card_expiring = verifications.filter(id_card_expiry_date=target_date)
        for ver in id_card_expiring:
            try:
                title = "⚠️ ID Card Expiring Soon"
                body = f"Your identity document expires {label}. Please update it to avoid service interruption."
                send_notification(ver.driver.user, title, body, type='PUSH')
                logger.info(f"Sent ID card expiry notification ({days} days) to user {ver.driver.user.email}")
            except Exception as e:
                logger.error(f"Error notifying ID card expiry for {ver.driver}: {e}")

        # 2. Vehicle Documents (Insurance & Roadworthy)
        vehicles = Vehicle.objects.filter(is_verified=True, is_active=True)

        # Insurance Expiration
        insurance_expiring = vehicles.filter(insurance_expiry=target_date)
        for veh in insurance_expiring:
            try:
                title = "⚠️ Vehicle Insurance Expiring Soon"
                body = f"The insurance for your vehicle ({veh.make} {veh.model}) expires {label}. Please upload your new document to stay active."
                send_notification(veh.driver.user, title, body, type='PUSH')
                logger.info(f"Sent insurance expiry notification ({days} days) to user {veh.driver.user.email}")
            except Exception as e:
                logger.error(f"Error notifying insurance expiry for vehicle {veh}: {e}")

        # Roadworthy Expiration
        roadworthy_expiring = vehicles.filter(roadworthy_expiry=target_date)
        for veh in roadworthy_expiring:
            try:
                title = "⚠️ Roadworthy Certificate Expiring Soon"
                body = f"The roadworthy certificate for your vehicle ({veh.make} {veh.model}) expires {label}. Please upload your new certificate to stay active."
                send_notification(veh.driver.user, title, body, type='PUSH')
                logger.info(f"Sent roadworthy expiry notification ({days} days) to user {veh.driver.user.email}")
            except Exception as e:
                logger.error(f"Error notifying roadworthy expiry for vehicle {veh}: {e}")
