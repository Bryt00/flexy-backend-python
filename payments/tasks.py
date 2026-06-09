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
            
            # Recalculate aggregates in the background to prevent API locking
            from django.db.models import Sum, Count
            from django.utils import timezone
            from datetime import timedelta
            from .models import DriverEarningsSummary

            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)

            base_qs = wallet.transactions.filter(type='off_app_sale', status='completed')
            
            today_total = base_qs.filter(created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0.0
            weekly_total = base_qs.filter(created_at__gte=week_start).aggregate(total=Sum('amount'))['total'] or 0.0
            overall_agg = base_qs.aggregate(total=Sum('amount'), count=Count('id'))
            all_time_total = overall_agg['total'] or 0.0
            ride_count = overall_agg['count'] or 0

            summary, _ = DriverEarningsSummary.objects.get_or_create(user_id=driver_user_id)
            summary.today_sales = float(today_total)
            summary.weekly_sales = float(weekly_total)
            summary.total_sales = float(all_time_total)
            summary.ride_count = ride_count
            summary.save()

            print(f"Task: Cached updated earnings for driver {driver_user_id}")
    except Exception as e:
        print(f"Error processing earnings: {e}")
