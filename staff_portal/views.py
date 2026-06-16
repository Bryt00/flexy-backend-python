from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core_auth.models import User
from profiles.models import DriverVerification, Profile
from vehicles.models import Vehicle

# --- DECORATORS ---

def is_super_admin(user):
    return user.is_authenticated and user.role == 'super_admin'

def is_finance(user):
    return user.is_authenticated and user.role in ['finance', 'super_admin']

def is_support(user):
    return user.is_authenticated and user.role in ['support', 'admin', 'super_admin']

def is_admin_or_super(user):
    return user.is_authenticated and user.role in ['admin', 'super_admin']

def is_staff_portal_user(user):
    return user.is_authenticated and user.role in ['support', 'finance', 'admin', 'super_admin']

# --- AUTHENTICATION ---

def portal_login(request):
    if request.user.is_authenticated and is_staff_portal_user(request.user):
        return redirect('staff_portal:portal_redirect')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if is_staff_portal_user(user):
                login(request, user)
                return redirect('staff_portal:portal_redirect')
            else:
                messages.error(request, "Access Denied: You do not have staff portal access.")
                logout(request)
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'staff_portal/login.html')

def portal_logout(request):
    logout(request)
    return redirect('staff_portal:login')

@login_required(login_url='staff_portal:login')
@user_passes_test(is_staff_portal_user, login_url='staff_portal:login')
def portal_redirect(request):
    """Redirects the user to their appropriate dashboard based on their highest role."""
    role = request.user.role
    if role == 'super_admin':
        return redirect('staff_portal:master_dashboard')
    elif role == 'finance':
        return redirect('staff_portal:finance_dashboard')
    elif role in ['support', 'admin']:
        return redirect('staff_portal:support_dashboard')
    else:
        # Fallback (shouldn't be reached due to decorator)
        return redirect('staff_portal:login')

# --- DASHBOARDS ---

from django.db.models.functions import TruncDay
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import json
from rides.models import Ride, Incident
from payments.models import Transaction

@login_required(login_url='staff_portal:login')
@user_passes_test(is_super_admin, login_url='staff_portal:login')
def master_dashboard(request):
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Ride Volume
    rides_by_day = list(Ride.objects.filter(
        created_at__gte=seven_days_ago
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day'))

    # Revenue
    revenue_by_day = list(Transaction.objects.filter(
        created_at__gte=seven_days_ago,
        payment_status='success'
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('amount')
    ).order_by('day'))
    
    # Build chart data (last 7 days sequentially)
    labels = []
    rides_data = []
    revenue_data = []
    
    for i in range(6, -1, -1):
        target_date = (timezone.now() - timedelta(days=i)).date()
        labels.append(target_date.strftime('%a'))
        
        # Match rides
        r_match = next((item for item in rides_by_day if item['day'].date() == target_date), None)
        rides_data.append(r_match['count'] if r_match else 0)
        
        # Match revenue
        rev_match = next((item for item in revenue_by_day if item['day'].date() == target_date), None)
        revenue_data.append(rev_match['total'] if rev_match and rev_match['total'] else 0)

    context = {
        'total_users': User.objects.count(),
        'total_drivers': Profile.objects.filter(user__role='driver').count(),
        'pending_verifications': DriverVerification.objects.filter(status='pending').count(),
        'chart_labels': json.dumps(labels),
        'rides_data': json.dumps(rides_data),
        'revenue_data': json.dumps(revenue_data),
    }
    return render(request, 'staff_portal/dashboards/master.html', context)

from core_auth.models import User

@login_required(login_url='staff_portal:login')
@user_passes_test(is_admin_or_super, login_url='staff_portal:login')
def global_users(request):
    query = request.GET.get('q', '')
    users_qs = User.objects.all().order_by('-created_at')
    if query:
        users_qs = users_qs.filter(Q(email__icontains=query) | Q(role__icontains=query))
        
    paginator = Paginator(users_qs, 20)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    return render(request, 'staff_portal/dashboards/global_users.html', {'users': users, 'query': query})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_admin_or_super, login_url='staff_portal:login')
def user_detail(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Admin & Super Admin can toggle suspension
        if action == 'toggle_suspension':
            if target_user.role == 'super_admin' and request.user.role != 'super_admin':
                messages.error(request, "You cannot suspend a super administrator.")
            else:
                target_user.is_active = not target_user.is_active
                target_user.save()
                status = "activated" if target_user.is_active else "suspended"
                messages.success(request, f"User {target_user.email} has been {status}.")
                
        # Only Super Admin can change roles or edit core details
        elif action == 'update_profile' and request.user.role == 'super_admin':
            new_role = request.POST.get('role')
            new_email = request.POST.get('email')
            is_verified = request.POST.get('is_email_verified') == 'on'
            
            if new_role and new_role in dict(User.ROLE_CHOICES):
                target_user.role = new_role
            if new_email:
                target_user.email = new_email
            target_user.is_email_verified = is_verified
            target_user.save()
            messages.success(request, f"Profile updated for {target_user.email}.")
            
        return redirect('staff_portal:user_detail', user_id=target_user.id)
        
    return render(request, 'staff_portal/dashboards/user_detail.html', {'target_user': target_user})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_admin_or_super, login_url='staff_portal:login')
def platform_settings(request):
    from core_settings.models import SiteSetting, PricingRule
    
    if request.method == 'POST' and request.user.role == 'super_admin':
        action = request.POST.get('action')
        
        if action == 'update_site_setting':
            setting_id = request.POST.get('setting_id')
            new_value = request.POST.get('value')
            setting = get_object_or_404(SiteSetting, id=setting_id)
            setting.value = new_value
            setting.save()
            messages.success(request, f"Setting '{setting.key}' updated successfully.")
            
        elif action == 'update_pricing_rule':
            rule_id = request.POST.get('rule_id')
            rule = get_object_or_404(PricingRule, id=rule_id)
            
            try:
                rule.base_fare = float(request.POST.get('base_fare', rule.base_fare))
                rule.per_km_rate = float(request.POST.get('per_km_rate', rule.per_km_rate))
                rule.per_minute_rate = float(request.POST.get('per_minute_rate', rule.per_minute_rate))
                rule.surge_multiplier = float(request.POST.get('surge_multiplier', rule.surge_multiplier))
                rule.is_active = request.POST.get('is_active') == 'on'
                rule.save()
                messages.success(request, f"Pricing rule updated successfully.")
            except ValueError:
                messages.error(request, "Invalid numeric values provided.")
                
        return redirect('staff_portal:platform_settings')

    settings = SiteSetting.objects.all()
    pricing_rules = PricingRule.objects.all()
    return render(request, 'staff_portal/dashboards/platform_settings.html', {'settings': settings, 'pricing_rules': pricing_rules})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_finance, login_url='staff_portal:login')
def finance_dashboard(request):
    query = request.GET.get('q', '')
    transactions_qs = Transaction.objects.all().order_by('-created_at')
    
    if query:
        transactions_qs = transactions_qs.filter(
            Q(id__icontains=query) | 
            Q(type__icontains=query) | 
            Q(payment_status__icontains=query)
        )
        
    paginator = Paginator(transactions_qs, 20)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    revenue_today = Transaction.objects.filter(
        created_at__gte=timezone.now().replace(hour=0, minute=0, second=0),
        payment_status='success'
    ).aggregate(Sum('amount'))['amount__sum'] or 0.0
    
    from payments.models import Wallet
    pending_payouts_count = Wallet.objects.filter(user__role='driver', balance__gt=0).count()
    
    context = {
        'revenue_today': revenue_today,
        'pending_payouts': pending_payouts_count,
        'transactions': transactions,
        'query': query,
    }
    return render(request, 'staff_portal/dashboards/finance.html', context)

@login_required(login_url='staff_portal:login')
@user_passes_test(is_finance, login_url='staff_portal:login')
def payout_queue(request):
    from payments.models import Wallet
    wallets = Wallet.objects.filter(user__role='driver', balance__gt=0).select_related('user')
    return render(request, 'staff_portal/dashboards/payout_queue.html', {'wallets': wallets})

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import uuid

@login_required(login_url='staff_portal:login')
@user_passes_test(is_finance, login_url='staff_portal:login')
def execute_payout(request, wallet_id):
    if request.method == 'POST':
        from payments.models import Wallet, Transaction
        wallet = get_object_or_404(Wallet, id=wallet_id, user__role='driver')
        
        if wallet.balance > 0:
            amount_to_pay = wallet.balance
            
            # 1. Deduct balance
            wallet.balance = 0
            wallet.save()
            
            # 2. Record Transaction
            Transaction.objects.create(
                wallet=wallet,
                amount=-amount_to_pay,
                type='payout',
                description='Driver Earnings Payout (Simulated)',
                status='completed',
                payment_status='success',
                paystack_reference=f"sim_{uuid.uuid4().hex[:10]}"
            )
            
            messages.success(request, f"Successfully processed payout of GHS {amount_to_pay:.2f} for {wallet.user.email}")
        else:
            messages.error(request, "This wallet has no pending balance.")
            
    return redirect('staff_portal:payout_queue')

import csv
from django.http import HttpResponse

@login_required(login_url='staff_portal:login')
@user_passes_test(is_finance, login_url='staff_portal:login')
def revenue_reports(request):
    from payments.models import Transaction
    
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="revenue_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Transaction ID', 'Amount', 'Type', 'Status', 'Payment Method'])
        
        txs = Transaction.objects.filter(payment_status='success').order_by('-created_at')
        for tx in txs:
            writer.writerow([tx.created_at.strftime('%Y-%m-%d %H:%M:%S'), str(tx.id), tx.amount, tx.type, tx.status, tx.payment_method])
            
        return response
        
    transactions = Transaction.objects.filter(payment_status='success').order_by('-created_at')
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff_portal/dashboards/revenue_reports.html', {'transactions': page_obj})

from django.conf import settings

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def support_dashboard(request):
    active_rides = list(Ride.objects.filter(status='in_progress').values(
        'id', 'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng',
        'last_lat_update', 'last_lng_update', 'rider_name'
    ))
    context = {
        'pending_verifications': DriverVerification.objects.filter(status='pending')[:10],
        'active_rides_json': json.dumps(active_rides, default=str),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'staff_portal/dashboards/support.html', context)

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def ride_history(request):
    query = request.GET.get('q', '')
    rides_qs = Ride.objects.all().select_related('rider', 'driver').order_by('-created_at')
    
    if query:
        rides_qs = rides_qs.filter(
            Q(id__icontains=query) | 
            Q(rider__email__icontains=query) | 
            Q(driver__email__icontains=query) | 
            Q(status__icontains=query)
        )
        
    paginator = Paginator(rides_qs, 20)
    page_number = request.GET.get('page')
    rides = paginator.get_page(page_number)
    
    return render(request, 'staff_portal/dashboards/ride_history.html', {'rides': rides, 'query': query})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def ride_detail(request, ride_id):
    ride = get_object_or_404(Ride.objects.select_related('rider', 'driver'), id=ride_id)
    incidents = ride.incidents.all().order_by('-created_at')
    
    # Normally we'd get RideStops here as well if they exist
    # ride_stops = ride.ridestop_set.all().order_by('stop_order')
    
    context = {
        'ride': ride,
        'incidents': incidents,
    }
    return render(request, 'staff_portal/dashboards/ride_detail.html', context)

from django.shortcuts import get_object_or_404
from notification.providers.fcm import FCMProvider

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def review_document(request, pk):
    verification = get_object_or_404(DriverVerification, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            verification.status = 'approved'
            verification.is_verified = True
            verification.save()
            messages.success(request, f"Successfully approved documents for {verification.driver.email}")
        elif action == 'reject':
            verification.status = 'rejected'
            verification.rejected_reason = request.POST.get('rejected_reason', 'Documents did not meet criteria.')
            verification.save()
            
            # Send Push Notification to Driver
            fcm = FCMProvider()
            fcm.send_push(
                user_id=verification.driver.user.id,
                title="Documents Rejected",
                message=f"Your documents were rejected: {verification.rejected_reason}. Please re-upload.",
                data={'type': 'document_rejected'}
            )
            
            messages.warning(request, f"Rejected documents for {verification.driver.email}")
            
        return redirect('staff_portal:support_dashboard')

    return render(request, 'staff_portal/dashboards/document_review.html', {'verification': verification})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def disputes_dashboard(request):
    incidents = Incident.objects.filter(status='ACTIVE').order_by('-created_at')
    return render(request, 'staff_portal/dashboards/disputes.html', {'incidents': incidents})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def dispute_detail(request, incident_id):
    incident = get_object_or_404(Incident.objects.select_related('ride', 'reporter'), id=incident_id)
    return render(request, 'staff_portal/dashboards/dispute_detail.html', {'incident': incident})

@login_required(login_url='staff_portal:login')
@user_passes_test(is_support, login_url='staff_portal:login')
def resolve_dispute(request, incident_id):
    if request.method == 'POST':
        incident = get_object_or_404(Incident, id=incident_id)
        incident.status = 'RESOLVED'
        incident.save()
        messages.success(request, f"Dispute {incident.id} marked as resolved.")
        return redirect('staff_portal:disputes_dashboard')
    return redirect('staff_portal:dispute_detail', incident_id=incident_id)

# --- AD OPERATIONS ---

@login_required(login_url='staff_portal:login')
@user_passes_test(is_super_admin, login_url='staff_portal:login')
def ad_dashboard(request):
    from advertising.models import AdBooking
    
    status_filter = request.GET.get('status', '')
    ads_qs = AdBooking.objects.all().order_by('-created_at')
    
    if status_filter:
        ads_qs = ads_qs.filter(status=status_filter)
    
    # Stats
    pending_count = AdBooking.objects.filter(status='PENDING_REVIEW').count()
    live_count = AdBooking.objects.filter(status='LIVE').count()
    total_ad_revenue = AdBooking.objects.filter(payment_status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
    
    from advertising.models import AdSlotCapacity
    slot_config = AdSlotCapacity.get_solo()
    
    paginator = Paginator(ads_qs, 20)
    page_number = request.GET.get('page')
    ads = paginator.get_page(page_number)
    
    context = {
        'ads': ads,
        'pending_count': pending_count,
        'live_count': live_count,
        'total_ad_revenue': total_ad_revenue,
        'current_status': status_filter,
        'slot_config': slot_config,
    }
    return render(request, 'staff_portal/dashboards/ad_dashboard.html', context)

@login_required(login_url='staff_portal:login')
@user_passes_test(is_super_admin, login_url='staff_portal:login')
def ad_review(request, ad_id):
    from advertising.models import AdBooking
    
    ad = get_object_or_404(AdBooking, id=ad_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            ad.status = 'APPROVED'
            ad.save()  # pre_save signal fires EmailService.send_ad_status_email
            messages.success(request, f"Approved ad for '{ad.business_name}'. Approval email sent to {ad.contact_email}.")
            
        elif action == 'reject':
            ad.status = 'REJECTED'
            ad.rejection_reason = request.POST.get('rejection_reason', 'Creative does not meet our guidelines.')
            ad.save()  # pre_save signal fires rejection email
            messages.warning(request, f"Rejected ad for '{ad.business_name}'.")
            
        elif action == 'go_live':
            ad.status = 'LIVE'
            ad.save()
            messages.success(request, f"Ad for '{ad.business_name}' is now LIVE!")
        
        return redirect('staff_portal:ad_dashboard')
    
    # Get analytics if they exist
    analytics = getattr(ad, 'analytics', None)
    
    return render(request, 'staff_portal/dashboards/ad_review.html', {
        'ad': ad,
        'analytics': analytics,
    })

@login_required(login_url='staff_portal:login')
@user_passes_test(is_super_admin, login_url='staff_portal:login')
def ad_slot_config(request):
    from advertising.models import AdSlotCapacity
    
    config = AdSlotCapacity.get_solo()
    
    if request.method == 'POST':
        try:
            config.max_ads_per_week = int(request.POST.get('max_ads_per_week', config.max_ads_per_week))
            config.price_per_week_ghs = float(request.POST.get('price_per_week_ghs', config.price_per_week_ghs))
            config.save()
            messages.success(request, "Ad slot configuration updated successfully.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid values. Please enter valid numbers.")
    
    return redirect('staff_portal:ad_dashboard')

