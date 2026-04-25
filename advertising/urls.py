from django.urls import path
from . import views

urlpatterns = [
    path('active/', views.ActiveAdsAPIView.as_view(), name='ads_active'),
]
