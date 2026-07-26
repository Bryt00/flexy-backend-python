from celery import shared_task
from django.db import transaction
from core_auth.models import User
from .models import Wallet, Transaction, DriverEarningsSummary

def process_ride_earnings_sync(driver_user_id, amount, ride_id, metadata=None):
    try:
        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(user_id=driver_user_id)
            
            meta = metadata or {}
            target_id = meta.get('ride_id') or meta.get('delivery_id') or str(ride_id)
            
            # Check if transaction already logged for this ride/delivery
            tx_exists = Transaction.objects.filter(wallet=wallet, metadata__ride_id=str(target_id)).exists() or \
                        Transaction.objects.filter(wallet=wallet, metadata__delivery_id=str(target_id)).exists()
            
            if not tx_exists:
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    type='off_app_sale', 
                    status='completed',
                    metadata=meta,
                    description=f"Earnings for ride/delivery {target_id}"
                )
            
            # Invalidate earnings cache
            from core_auth.cache_utils import invalidate_user_cache
            invalidate_user_cache(driver_user_id, 'earnings')
            invalidate_user_cache(driver_user_id, 'pay_stats')
    except Exception as e:
        print(f"Error processing earnings: {e}")

@shared_task
def process_ride_earnings(driver_user_id, amount, ride_id, metadata=None):
    process_ride_earnings_sync(driver_user_id, amount, ride_id, metadata)
