from django.urls import path
from . import website_views

urlpatterns = [
    path('', website_views.AdLandingView.as_view(), name='advertise_landing'),
    path('apply/', website_views.AdApplyView.as_view(), name='advertise_apply'),
    path('review/', website_views.AdReviewView.as_view(), name='advertise_review'),
    path('success/', website_views.AdSuccessView.as_view(), name='advertise_success'),
    path('dashboard/', website_views.AdDashboardView.as_view(), name='advertise_dashboard'),
    path('preview/', website_views.AdPreviewView.as_view(), name='advertise_preview'),
]

