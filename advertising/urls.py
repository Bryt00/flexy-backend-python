from django.urls import path
from . import views

urlpatterns = [
    path('active/', views.ActiveAdsAPIView.as_view(), name='ads_active'),
    path('impression/', views.AdImpressionAPIView.as_view(), name='ad_impression'),
    path('click/<uuid:ad_id>/', views.AdClickRedirectView.as_view(), name='ad_click'),
]
