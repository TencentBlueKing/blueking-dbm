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
    list_clusters_by_hosts,
    list_my_redis_bizs,
    redis_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.cluster_meta import (
    ClusterTopoOutputSerializer,
    RedisBizDetailSerializer,
    RedisBizInputSerializer,
    RedisBizNameInputSerializer,
    RedisClustersOutputSerializer,
    RedisEmptyInputSerializer,
    RedisHostClusterOutputSerializer,
    RedisHostInputSerializer,
    RedisMastersSummarySerializer,
    RedisProxiesSummarySerializer,
    RedisTopoInputSerializer,
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
        description=str(
            _(
                """
查询指定集群的拓扑部署信息，包括集群基本信息、存储实例统计、代理实例统计、机器分布情况等详细信息
## 适用场景

1. **容量规划**: 查看集群节点数、机器数，评估资源使用情况
2. **容灾分析**: 查看子Zone分布，评估容灾能力
3. **版本管理**: 查看实例版本分布，规划升级计划
4. **故障排查**: 查看节点状态分布，快速定位异常节点
5. **成本分析**: 查看设备规格分布，评估资源成本

## 错误处理
- 如果集群不存在，返回错误信息：`{"error": "集群不存在"}`

## 结果展示
1. 存储层和接入层: 全部信息要融合成多行多列并且用一个表格展示
2. 基础信息部分: 采用分层结构化展示方式
"""
            )
        ),
        request_slz=RedisTopoInputSerializer,
        response_slz=ClusterTopoOutputSerializer,
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

    @mcp_tools_api_decorator(
        description=str(_("根据输入的IP列表;查询Redis集群列表")),
        request_slz=RedisHostInputSerializer,
        response_slz=RedisHostClusterOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_clusters_by_hosts(self, request, *args, **kwargs):
        hosts = self.get_param("hosts")
        return Response(list_clusters_by_hosts(hosts=hosts))
