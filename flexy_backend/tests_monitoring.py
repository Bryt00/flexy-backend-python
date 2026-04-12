from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_sentry(request):
    division_by_zero = 1 / 0
    return HttpResponse("Error triggered")
