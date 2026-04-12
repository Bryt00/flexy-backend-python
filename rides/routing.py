from django.urls import path, re_path
from . import consumers
from notification.consumers import NotificationConsumer

websocket_urlpatterns = [
    # Global Admin Map
    path('ws/rides/global/', consumers.GlobalRideConsumer.as_asgi()),
    
    # Mobile App Routes (matching Go subpaths)
    path('v1/rides/<uuid:ride_id>/track/driver', consumers.RideConsumer.as_asgi()),
    path('v1/rides/<uuid:ride_id>/track/rider', consumers.RideConsumer.as_asgi()),
    path('v1/rides/discovery', consumers.RideConsumer.as_asgi()),
    path('v1/notifications/ws', NotificationConsumer.as_asgi()),
]
