# your_app/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # URL mà frontend sẽ kết nối tới
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]