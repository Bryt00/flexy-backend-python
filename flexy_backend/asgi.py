import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
import rides.routing
import courier.routing
from .middleware import QueryAuthMiddleware

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        QueryAuthMiddleware(
            AuthMiddlewareStack(
                URLRouter(
                    rides.routing.websocket_urlpatterns +
                    courier.routing.websocket_urlpatterns
                )
            )
        )
    ),
})
