"""
ASGI config for Thesis project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thesis.settings')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import investment_advisor.routing

application = ProtocolTypeRouter({
    # Xử lý HTTP request (vẫn như Django bình thường)
    "http": django_asgi_app,

    # Xử lý WebSocket request
    "websocket": AuthMiddlewareStack(
        URLRouter(
            investment_advisor.routing.websocket_urlpatterns
        )
    ),
})
