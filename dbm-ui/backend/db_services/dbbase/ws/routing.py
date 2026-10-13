# -*- coding: utf-8 -*-
from django.urls import path

from backend.db_services.dbbase.ws.consumers import WebConsoleConsumer

websocket_urlpatterns = [
    path("ws/dbbase/webconsole/", WebConsoleConsumer.as_asgi()),
]
