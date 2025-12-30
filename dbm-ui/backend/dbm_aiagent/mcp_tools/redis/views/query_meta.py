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
from backend.dbm_aiagent.mcp_tools.redis.impl.cluster_topo import (
    cluster_masters,
    cluster_overview,
    cluster_proxies,
    instance_tuple,
    redis_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.cluster_topo import (
    RedisAddrSerializer,
    RedisBizInputSerializer,
    RedisClustersOutputSerializer,
    RedisInstanceTupleSerializer,
    RedisNodesSummarySerializer,
    RedisTopoInputSerializer,
    RedisTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

"""
meta 相关的query
"""


class RedisQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的Redis集群列表")),
        request_slz=RedisBizInputSerializer,
        response_slz=RedisClustersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_redis_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")

        return Response(redis_list_clusters(bk_biz_id=bk_biz_id))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群元数据")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群的Proxy节点信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_proxies(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_proxies(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群的Master节点信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisNodesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_masters(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_masters(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 实例的主从关系")),
        request_slz=RedisAddrSerializer,
        response_slz=RedisInstanceTupleSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_instance_tuple(self, request, *args, **kwargs):
        address = self.get_param("address")
        return Response(instance_tuple(addr=address))
