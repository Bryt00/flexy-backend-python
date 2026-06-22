from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import SiteSetting
from .serializers import SiteSettingSerializer
from core_auth.cache_utils import conditional_api_response

class SiteSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows site settings to be viewed.
    """
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)
