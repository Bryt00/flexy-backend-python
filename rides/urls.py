from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RideViewSet

router = DefaultRouter(trailing_slash=False) # Match Go's no-trailing-slash behavior where applicable
router.register(r'', RideViewSet)

urlpatterns = [
    # Custom mappings for exact Go parity
    path('', include(router.urls)),
    path('<uuid:pk>/accept', RideViewSet.as_view({'put': 'accept', 'post': 'accept'})),
    path('<uuid:pk>/sos', RideViewSet.as_view({'post': 'sos'})),
    path('<uuid:pk>/chat', RideViewSet.as_view({'get': 'chat_history'})),
]
