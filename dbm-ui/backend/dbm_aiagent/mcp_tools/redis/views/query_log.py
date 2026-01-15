"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_log import get_proxy_slowlog, get_redis_slowlog
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_log import (
    RedisSlowlogInputSerializer,
    RedisSlowlogResponseSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")


class RedisQueryLogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询Redis慢查询日志(slowlog)，包括执行时间、命令内容、客户端信息等。可用于分析Redis性能问题和慢查询优化")),
        request_slz=RedisSlowlogInputSerializer,
        response_slz=RedisSlowlogResponseSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_slowlog",
    )
    def get_redis_slowlog(self, request, *args, **kwargs):
        """获取Redis慢查询日志"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("immute_domain")
        count = self.get_param("count", 10)

        return Response(get_redis_slowlog(redis_addr=redis_addr, immute_domain=immute_domain, count=count))

    @mcp_tools_api_decorator(
        description=str(_("查询Proxy慢日志")),
        request_slz=RedisSlowlogInputSerializer,
        response_slz=RedisSlowlogResponseSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_log",
    )
    def get_proxy_slowlog(self, request, *args, **kwargs):
        """获取Proxy实例的慢日志"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("immute_domain")
        return Response(get_proxy_slowlog(addr=redis_addr, immute_domain=immute_domain))
