from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import SiteSetting
from .serializers import SiteSettingSerializer
from core_auth.cache_utils import cached_api_response

class SiteSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows site settings to be viewed.
    """
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'

    def list(self, request, *args, **kwargs):
        def fetch_settings():
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return cached_api_response(request, 'site_settings', timeout=900, fetcher=fetch_settings, global_cache=True)
