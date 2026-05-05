from rest_framework import viewsets, permissions
from .models import SiteSetting
from .serializers import SiteSettingSerializer

class SiteSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows site settings to be viewed.
    """
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'
