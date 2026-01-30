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

from backend.dbm_aiagent.mcp_tools.redis.views.job import RedisJobMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.metrics import RedisMetricsMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.query_alarm import RedisQueryALARMMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.query_log import RedisQueryLogMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.query_meta import RedisQueryMetaMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.query_status import RedisQueryStatusMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.redis.views.redis_bill_mcp import RedisBillMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

# 与 元数据相关的 query
routers.register(r"", RedisQueryMetaMcpToolsViewSet, basename="mcp-redis-query-meta")
# 与 实力状态相关的 query ； 需要登陆实例才能获取的信息
routers.register(r"", RedisQueryStatusMcpToolsViewSet, basename="mcp-redis-query-status")
# 与 dbm 交互 创建单据类的 操作
routers.register(r"", RedisBillMcpToolsViewSet, basename="mcp-redis-bill")
# 与 job 平台交互的 操作
routers.register(r"", RedisJobMcpToolsViewSet, basename="mcp-redis-job")
# 与 日志 相关的查询
routers.register(r"", RedisQueryLogMcpToolsViewSet, basename="mcp-redis-query-log")

# 与 告警 相关的查询
routers.register(r"", RedisQueryALARMMcpToolsViewSet, basename="mcp-redis-query-alrams")
# # 与 metric相关的 ； exporter 上报的数据
routers.register(r"", RedisMetricsMcpToolsViewSet, basename="mcp-redis-query-metric")

# 与 告警 相关的 2do
# 与 其他组件----
# routers.register(r"", RedisMetaQueryMcpToolsViewSet, basename="mcp-redis-meta-query")

urlpatterns = routers.urls
