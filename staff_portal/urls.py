from django.urls import path
from . import views

app_name = 'staff_portal'

urlpatterns = [
    path('login/', views.portal_login, name='login'),
    path('logout/', views.portal_logout, name='logout'),
    path('', views.portal_redirect, name='portal_redirect'),
    path('master/', views.master_dashboard, name='master_dashboard'),
    path('master/users/', views.global_users, name='global_users'),
    path('master/users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('master/settings/', views.platform_settings, name='platform_settings'),
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/payouts/', views.payout_queue, name='payout_queue'),
    path('finance/payouts/execute/<uuid:wallet_id>/', views.execute_payout, name='execute_payout'),
    path('finance/revenue/', views.revenue_reports, name='revenue_reports'),
    path('support/', views.support_dashboard, name='support_dashboard'),
    path('support/verifications/', views.driver_verifications, name='driver_verifications'),
    path('support/verifications/vehicle/<uuid:vehicle_id>/', views.review_secondary_vehicle, name='review_secondary_vehicle'),
    path('support/rides/', views.ride_history, name='ride_history'),
    path('support/rides/<uuid:ride_id>/', views.ride_detail, name='ride_detail'),
    path('support/document/<int:pk>/', views.review_document, name='review_document'),
    path('support/disputes/', views.disputes_dashboard, name='disputes_dashboard'),
    path('support/disputes/<uuid:incident_id>/', views.dispute_detail, name='dispute_detail'),
    path('support/disputes/<uuid:incident_id>/resolve/', views.resolve_dispute, name='resolve_dispute'),
    path('support/deliveries/', views.delivery_history, name='delivery_history'),
    path('support/deliveries/<uuid:delivery_id>/', views.delivery_detail, name='delivery_detail'),
    path('master/subscriptions/', views.subscriptions_overview, name='subscriptions_overview'),
    path('master/subscriptions/<uuid:sub_id>/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('master/audit/', views.audit_log, name='audit_log'),
    path('master/audit/fraud/', views.fraud_flags, name='fraud_flags'),
    path('ads/', views.ad_dashboard, name='ad_dashboard'),
    path('ads/review/<uuid:ad_id>/', views.ad_review, name='ad_review'),
    path('ads/config/', views.ad_slot_config, name='ad_slot_config'),
]
