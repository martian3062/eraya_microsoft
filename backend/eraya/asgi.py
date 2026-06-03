import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eraya.settings.development')
django.setup()

from core.telemetry import setup_telemetry          # noqa: E402
setup_telemetry()

from apps.agents.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
