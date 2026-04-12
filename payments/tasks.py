from celery import shared_task
from django.db import transaction
from core_auth.models import User
from .models import Wallet, Transaction

@shared_task
def process_ride_earnings(driver_user_id, amount, ride_id, metadata=None):
    try:
        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(user_id=driver_user_id)
            
            # Create transaction record
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                type='deposit', # Go called it earnings, we use deposit for balance increase
                reference_id=str(ride_id),
                status='completed',
                description=f"Earnings for ride {ride_id}"
            )
            
            # Update wallet balance
            wallet.balance += amount
            wallet.save()
            
            print(f"Task: Processed ${amount} earnings for driver {driver_user_id} on ride {ride_id}")
    except Exception as e:
        print(f"Error processing earnings: {e}")
