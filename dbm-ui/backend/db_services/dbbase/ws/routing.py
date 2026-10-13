# -*- coding: utf-8 -*-
from django.urls import path

from backend import env
from backend.db_services.dbbase.ws.consumers import WebConsoleConsumer
from backend.db_services.dbbase.ws.external_proxy import ExternalWebConsoleConsumer

# 外部环境只连接 APIGW，不在本地查询集群、访问云区域或执行 SQL。
webconsole_consumer = (
    ExternalWebConsoleConsumer if env.ENABLE_EXTERNAL_PROXY or env.ENABLE_OPEN_EXTERNAL_PROXY else WebConsoleConsumer
)

websocket_urlpatterns = [
    path("ws/dbbase/webconsole/", webconsole_consumer.as_asgi()),
]
