from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('v1/deliveries/<uuid:delivery_id>/track/sender', consumers.CourierConsumer.as_asgi()),
    path('v1/deliveries/<uuid:delivery_id>/track/courier', consumers.CourierConsumer.as_asgi()),
    path('v1/deliveries/discovery', consumers.CourierConsumer.as_asgi()),
]
