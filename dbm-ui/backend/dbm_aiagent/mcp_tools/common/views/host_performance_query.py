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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.host_performance_query import query_cluster_hosts_performance
from backend.dbm_aiagent.mcp_tools.common.serializers.host_performance_query import (
    ClusterHostPerformanceOutputSerializer,
    HostPerformanceByClusterInputSerializer,
    HostPerformanceByIpInputSerializer,
    SingleHostPerformanceOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.dbm_aiagent.utils import query_host_performance
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission, McpIsDbaPermission


class HostPerformanceQueryMcpToolsViewSet(McpToolsViewSet):
    """主机硬件与基线性能查询 MCP 工具"""

    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "根据主机 IP 与云区域查询该机型的 BaselineHost 与各挂载点的 BaselineDisk 性能指标；"
                "返回 machine 摘要、host_baseline、disks[].baseline。仅 DBA 可调用。"
            )
        ),
        request_slz=HostPerformanceByIpInputSerializer,
        response_slz=SingleHostPerformanceOutputSerializer,
        permission_classes=[McpIsDbaPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HOST_PERFORMANCE_QUERY],
        name_prefix="host_performance_query",
    )
    def query_host_performance_by_ip(self, request, *args, **kwargs):
        ip = self.get_param("ip")
        bk_cloud_id = self.get_param("bk_cloud_id")
        return Response(query_host_performance(ip=ip, bk_cloud_id=bk_cloud_id))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "根据集群 ID 或 immute 域名查询集群内各主机硬件与基线性能；"
                "每台 hosts 元素在单机结构外附带 instance_roles（本集群内 Storage 角色及 proxy）；"
                "可选 instance_roles 仅保留 StorageInstance.instance_role 命中或包含 proxy 时的 Proxy 机器。"
                "返回 cluster_id、immute_domain、hosts。需集群查看权限。"
            )
        ),
        request_slz=HostPerformanceByClusterInputSerializer,
        response_slz=ClusterHostPerformanceOutputSerializer,
        permission_classes=[McpIsDbaPermission, McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HOST_PERFORMANCE_QUERY],
        name_prefix="host_performance_query",
    )
    def query_host_performance_by_cluster(self, request, *args, **kwargs):
        cluster_id = self.get_param("cluster_id")
        cluster_domain = self.get_param("cluster_domain")
        instance_roles = self.get_param("instance_roles") or []

        if cluster_id is not None:
            cluster = Cluster.objects.get(id=int(cluster_id))
        else:
            cluster = Cluster.objects.get(immute_domain=cluster_domain)

        return Response(query_cluster_hosts_performance(cluster=cluster, instance_roles=instance_roles or None))
