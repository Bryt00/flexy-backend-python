from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RideViewSet, SystemSettingsView

router = DefaultRouter()
router.register(r'trips', RideViewSet, basename='ride')

urlpatterns = [
    # Router prefix 'trips' maintains detail endpoints, 
    # but we map root 'v1/rides/' actions explicitly for Go/Flutter parity
    path('', RideViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('history/', RideViewSet.as_view({'get': 'history'})),
    path('active/', RideViewSet.as_view({'get': 'active'})),
    path('scheduled/', RideViewSet.as_view({'get': 'scheduled'})),
    path('schedule/', RideViewSet.as_view({'post': 'schedule'})),
    path('favorites/', RideViewSet.as_view({'get': 'favorites', 'post': 'favorites'})),
    path('estimate/', RideViewSet.as_view({'get': 'estimate'})),
    
    # Detail actions
    path('<uuid:pk>/', RideViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('<uuid:pk>/status/', RideViewSet.as_view({'post': 'status', 'put': 'status', 'patch': 'status'})),
    path('<uuid:pk>/accept/', RideViewSet.as_view({'post': 'accept', 'put': 'accept'})),
    path('<uuid:pk>/cancel/', RideViewSet.as_view({'post': 'cancel'})),
    path('<uuid:pk>/sos/', RideViewSet.as_view({'post': 'sos'})),
    path('<uuid:pk>/rate/', RideViewSet.as_view({'post': 'rate'})),
    path('<uuid:pk>/chat/', RideViewSet.as_view({'get': 'chat_history'})),
    
    path('operations/settings/', SystemSettingsView.as_view(), name='system-settings'),
    path('', include(router.urls)),
]
