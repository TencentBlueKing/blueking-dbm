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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    auth_parse_bizs,
    auth_parse_clusters,
    auth_parse_hosts,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.cluster_meta import (
    cluster_basic_overview,
    cluster_proxies,
    cluster_proxy_overview,
    cluster_storage_overiew,
    get_cluster_storage_tuples,
    instance_detail,
    list_biz_by_name,
    list_clusters_by_hosts,
    list_my_redis_bizs,
    redis_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.cluster_meta import (
    ClusterInstancesDetailSerializer,
    ClusterStorageTuplesSerializer,
    RedisBizInputSerializer,
    RedisBizNameInputSerializer,
    RedisBizsListSerializer,
    RedisClusterBasicOutputSerializer,
    RedisClustersOutputSerializer,
    RedisClusterStorageDepOutputSerializer,
    RedisEmptyInputSerializer,
    RedisHostClusterOutputSerializer,
    RedisHostInputSerializer,
    RedisInstancesInputSerializer,
    RedisInstancesTopoSerializer,
    RedisListInstsTopoInputSerializer,
    RedisListStorageInstsInputSerializer,
    RedisProxiesSummarySerializer,
    RedisTopoInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission, McpDBManagePermission

logger = logging.getLogger("flow")

"""
meta 相关的query
"""


class RedisQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询当前用户负责管理的所有 Redis 业务列表，当用户未提供 bk_biz_id 时，应先调用此接口获取可用业务列表。")),
        request_slz=RedisEmptyInputSerializer,
        response_slz=RedisBizsListSerializer,
        permission_classes=[],
        mcp_auth_parser=None,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_redis_bizs(username=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("通过业务英文名（模糊匹配）查询业务信息，当用户提供了业务名称但未提供 bk_biz_id 时，应先调用此接口将名称转换为 bk_biz_id")),
        request_slz=RedisBizNameInputSerializer,
        response_slz=RedisBizsListSerializer,
        permission_classes=[],
        mcp_auth_parser=None,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_biz_by_name(self, request, *args, **kwargs):
        biz_name = self.get_param("biz_name")
        return Response(list_biz_by_name(biz_name=biz_name))

    @mcp_tools_api_decorator(
        description=str(_("查询指定业务（bk_biz_id）下的所有 Redis 集群列表，支持分页")),
        request_slz=RedisBizInputSerializer,
        response_slz=RedisClustersOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_redis_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        page = self.get_param("page", default_value=1)
        page_size = self.get_param("page_size", default_value=80)

        return Response(redis_list_clusters(bk_biz_id=bk_biz_id, page=page, page_size=page_size))

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的基本概览信息，需要提供集群域名（cluster_domain）。")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisClusterBasicOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def cluster_basic_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("cluster_domain")
        return Response(cluster_basic_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的 Proxy（代理层）实例统计摘要。适合快速了解集群代理层整体健康状况，不返回具体实例列表。")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisInstancesTopoSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def cluster_proxy_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("cluster_domain")
        return Response(cluster_proxy_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的存储层（redis_master 和 redis_slave）实例统计摘要，适合快速了解集群存储层整体规模和健康状况，不返回具体实例列表。")),
        request_slz=RedisTopoInputSerializer,
        response_slz=RedisClusterStorageDepOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def cluster_storage_overiew(self, request, *args, **kwargs):
        immute_domain = self.get_param("cluster_domain")
        return Response(cluster_storage_overiew(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的 Proxy 节点详细列表，支持通过 ips 参数过滤特定主机，支持分页参数")),
        request_slz=RedisListInstsTopoInputSerializer,
        response_slz=RedisProxiesSummarySerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_proxies(self, request, *args, **kwargs):
        immute_domain = self.get_param("cluster_domain")
        hosts = self.get_param("ips", default_value=[])  # 获取可选的 hosts 参数
        page = self.get_param("page", default_value=1)
        page_size = self.get_param("page_size", default_value=80)
        return Response(cluster_proxies(immute_domain=immute_domain, hosts=hosts, page=page, page_size=page_size))

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的存储节点主从关系对列表，支持通过 addrs 参数过滤与特定实例相关的主从对，支持分页。适合排查主从关系、定位某个实例的对端节点。")),
        request_slz=RedisListStorageInstsInputSerializer,
        response_slz=ClusterStorageTuplesSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_cluster_storageinstances(self, request, *args, **kwargs):
        addrs = self.get_param("addrs", default_value=[])  # 获取可选的 hosts 参数
        immute_domain = self.get_param("cluster_domain")
        page = self.get_param("page", default_value=1)
        page_size = self.get_param("page_size", default_value=80)
        return Response(
            get_cluster_storage_tuples(
                immute_domain=immute_domain, instance_addresses=addrs, page=page, page_size=page_size
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("根据输入的主机 IP 列表，反查这些主机所属的 Redis 集群信息。")),
        request_slz=RedisHostInputSerializer,
        response_slz=RedisHostClusterOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_hosts,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_clusters_by_hosts(self, request, *args, **kwargs):
        hosts = self.get_param("ips")
        return Response(list_clusters_by_hosts(hosts=hosts))

    @mcp_tools_api_decorator(
        description=str(_("查询指定集群内特定实例的详细信息，适合深入排查某个具体实例的配置和状态。")),
        request_slz=RedisInstancesInputSerializer,
        response_slz=ClusterInstancesDetailSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_META],
        name_prefix="redis_query_meta",
    )
    def list_instances_basicinfo(self, request, *args, **kwargs):
        addrs = self.get_param("addrs")
        immute_domain = self.get_param("cluster_domain")
        return Response(instance_detail(immute_domain=immute_domain, addrs=addrs))
