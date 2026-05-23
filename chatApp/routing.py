from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Matches ws://localhost:8000/ws/chat/
    re_path(r'^ws/chat/$', consumers.ChatConsumer.as_asgi()),
]
