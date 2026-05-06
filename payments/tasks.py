from celery import shared_task
from django.db import transaction
from core_auth.models import User
from .models import Wallet, Transaction

@shared_task
def process_ride_earnings(driver_user_id, amount, ride_id, metadata=None):
    try:
        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(user_id=driver_user_id)
            
            # Create transaction record for off-app sale tracker
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                type='off_app_sale', 
                status='completed',
                metadata=metadata or {},
                description=f"Sales record for ride {ride_id} (Collected Off-App)"
            )
            
            # wallet.balance update removed per user requirement: 
            # "payment of fare to driver is handled by the drivers themselves"
            
            print(f"Task: Logged ${amount} off-app sale for driver {driver_user_id} on ride {ride_id}")
    except Exception as e:
        print(f"Error processing earnings: {e}")
