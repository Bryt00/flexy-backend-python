from celery import shared_task
from django.utils import timezone
from .models import Campaign
from core_auth.models import User
from .utils import send_notification
import logging

logger = logging.getLogger(__name__)

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
