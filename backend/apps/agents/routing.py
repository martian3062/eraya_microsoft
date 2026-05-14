from django.urls import re_path
from .consumers import ErayaConsumer

websocket_urlpatterns = [
    re_path(r"ws/eraya/(?P<domain>\w+)/$", ErayaConsumer.as_asgi()),
    re_path(r"ws/eraya/$", ErayaConsumer.as_asgi()),
]
