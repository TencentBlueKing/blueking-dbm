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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.cluster_meta import (
    cluster_masters,
    cluster_overview,
    cluster_proxies,
    list_biz_by_name,
    list_my_redis_bizs,
    redis_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.cluster_meta import (
    RedisBizDetailSerializer,
    RedisBizInputSerializer,
    RedisBizNameInputSerializer,
    RedisClustersOutputSerializer,
    RedisEmptyInputSerializer,
    RedisMastersSummarySerializer,
    RedisProxiesSummarySerializer,
    RedisTopoInputSerializer,
    RedisTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
meta 相关的query
"""


class RedisQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询我负责的Redis业务列表")),
        request_slz=RedisEmptyInputSerializer,
        response_slz=RedisBizDetailSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        print("===>>> 我的id: {}".format(request.user))
        return Response(list_my_redis_bizs(userID=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("根据业务英文名查询业务详情")),
        request_slz=RedisBizNameInputSerializer,
        response_slz=RedisBizDetailSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        biz_name = self.get_param("biz_name")

        return Response(list_biz_by_name(biz_name=biz_name))

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的Redis集群列表")),
        request_slz=RedisBizInputSerializer,
        response_slz=RedisClustersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_redis_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")

        return Response(redis_list_clusters(bk_biz_id=bk_biz_id))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群的Proxy节点信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisProxiesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_proxies(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_proxies(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 Redis 集群的Master节点信息")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisMastersSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_masters(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_masters(immute_domain=immute_domain))
