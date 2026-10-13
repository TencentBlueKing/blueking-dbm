# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.db.backends.mysql.features import DatabaseFeatures

from blueking.mysql_patch import PatchFeatures

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.prod")

DatabaseFeatures.minimum_database_version = PatchFeatures.minimum_database_version

django_asgi_app = get_asgi_application()

from backend.db_services.dbbase.ws.middleware import DBMWebSocketAuthMiddleware  # noqa: E402
from backend.db_services.dbbase.ws.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": DBMWebSocketAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
