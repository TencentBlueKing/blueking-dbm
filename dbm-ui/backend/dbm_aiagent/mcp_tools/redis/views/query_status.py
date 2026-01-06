"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.serializers.cluster_meta import (
    RedisTopoInputSerializer,
    RedisTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

"""
meta 相关的query
"""


class RedisQueryStatusMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 实例运行状态信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def instance_version(self, request, *args, **kwargs):
        addr = self.get_param("addr")
        return Response({"func": "todo", "immute_domain": addr})

    def cluster_version(self, request, *args, **kwargs):
        cluster_domain = self.get_param("immute_domain")
        return Response({"func": "todo", "immute_domain": cluster_domain})
