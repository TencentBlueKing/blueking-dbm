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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsInstanceRole, MetricsStatsType, MetricType
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_metrics import (
    query_redis_metrics_series,
    query_redis_metrics_stats,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_metrics import (
    RedisMetricsSeriesInputSerializer,
    RedisMetricsSeriesOutputSerializer,
    RedisMetricsStatsInputSerializer,
    RedisMetricsStatsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission

logger = logging.getLogger("root")


class RedisMetricsMcpToolsViewSet(McpToolsViewSet):
    """Redis metrics MCP tools viewset for querying cluster performance metrics"""

    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=_(
            "Query Redis time-series metrics: cpu_usage, memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, latency_distribution. instance_role: redis_master|redis_slave|proxy. "
            "Aggregation: ip+port→INSTANCE, ip→MACHINE, else CLUSTER. group_by for result breakdown. "
            "Rules: latency_distribution→group_by=['bucket'] (proxy auto-set); port requires ip; "
            "keep max_len_datapoints<=15 to avoid context length issues; mermaid_code output AS-IS."
        ),
        request_slz=RedisMetricsSeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_series(self, request, *args, **kwargs):
        """Endpoint for querying Redis time-series data"""
        cluster_domain = self.get_param("cluster_domain")
        metric_type = MetricType(self.get_param("metric_type"))
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        instance_role = MetricsInstanceRole(self.get_param("instance_role", MetricsInstanceRole.MASTER.value))
        ip = self.get_param("ip")
        port = self.get_param("port")
        max_len_datapoints = self.get_param("max_len_datapoints")
        mermaid_format = self.get_param("mermaid_format", False)

        group_by_list = self.get_param("group_by")
        if group_by_list is not None and not isinstance(group_by_list, list):
            group_by_list = [group_by_list]
        group_by = [MetricsGroupBy(dim) for dim in group_by_list] if group_by_list else None

        result = query_redis_metrics_series(
            cluster_domain=cluster_domain,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
            instance_role=instance_role,
            ip=ip,
            port=port,
            max_len_datapoints=max_len_datapoints,
            mermaid_format=mermaid_format,
            group_by=group_by,
        )

        return Response(result)

    @mcp_tools_api_decorator(
        description=_(
            "Query Redis scalar statistics: cpu_usage, memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, latency_distribution. Returns min, max, avg, median, p95, cv, trend. "
            "instance_role: redis_master|redis_slave|proxy. "
            "Aggregation: ip+port→INSTANCE, ip→MACHINE, else CLUSTER. group_by for result breakdown. "
            "Rules: latency_distribution→group_by=['bucket'] (proxy auto-set); port requires ip."
        ),
        request_slz=RedisMetricsStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_stats(self, request, *args, **kwargs):
        """Endpoint for querying Redis scalar statistics"""
        cluster_domain = self.get_param("cluster_domain")
        metric_type = MetricType(self.get_param("metric_type"))
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        instance_role = MetricsInstanceRole(self.get_param("instance_role", MetricsInstanceRole.MASTER.value))
        ip = self.get_param("ip")
        port = self.get_param("port")
        max_len_datapoints = self.get_param("max_len_datapoints")
        stats_type = MetricsStatsType(self.get_param("stats_type", MetricsStatsType.VERTICAL.value))

        group_by_list = self.get_param("group_by")
        if group_by_list is not None and not isinstance(group_by_list, list):
            group_by_list = [group_by_list]
        group_by = [MetricsGroupBy(dim) for dim in group_by_list] if group_by_list else None

        result = query_redis_metrics_stats(
            cluster_domain=cluster_domain,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
            instance_role=instance_role,
            ip=ip,
            port=port,
            max_len_datapoints=max_len_datapoints,
            group_by=group_by,
            stats_type=stats_type,
        )

        return Response(result)
