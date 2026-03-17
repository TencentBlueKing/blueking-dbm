"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from rest_framework.routers import DefaultRouter

from backend.dbm_aiagent.mcp_tools.mongodb.views.query_alarm import MongoAlarmMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.mongodb.views.query_log import MongoLogMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.mongodb.views.query_meta import MongoMetaMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.mongodb.views.query_metrics import MongoMetricsMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register(r"", MongoMetaMcpToolsViewSet, basename="mcp-mongodb-meta")
routers.register(r"", MongoLogMcpToolsViewSet, basename="mcp-mongodb-log")
routers.register(r"", MongoAlarmMcpToolsViewSet, basename="mcp-mongodb-alarm")
routers.register(r"", MongoMetricsMcpToolsViewSet, basename="mcp-mongodb-metrics")

urlpatterns = routers.urls
