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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_metrics import MetricsInstanceRole, MetricType, query_redis_metrics
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_metrics import (
    RedisMetricsInputSerializer,
    RedisMetricsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


def build_metric_description(metric_name: str, supports_info: str) -> str:
    """Build a standardized metric query API description"""
    return _(
        f"Query {metric_name} metrics for a Redis cluster. "
        f"{supports_info} "
        "Returns either aggregated time series (mode='overall') or scalar statistics (mode='stats'). "
        "Time range: Specify start_time and end_time in ISO format (e.g., '2026-01-08T16:33:38+08:00'). "
        "Both are optional and default to last 30 minutes if not specified. "
        "Use detailed=True to get more granular dimensions (e.g., when user ask for per-IP metrics). "
        "Set mermaid_format=True to get pre-formatted mermaid xychart-beta code for visualization "
        "(only active when mode != 'stats'). Make sure max_len_datapoints<=15 for chart visualization. "
        "**IMPORTANT**: When mermaid_code is returned, DO NOT modify or regenerate it. "
        "Output the mermaid_code AS-IS and it'll be auto-rendering. "
        "Only provide label descriptions as separate text output."
    )


class RedisMetricsMcpToolsViewSet(McpToolsViewSet):
    """Redis metrics MCP tools viewset for querying cluster performance metrics"""

    default_permission_class = [DBManagePermission()]

    def _query_metrics_by_type(self, request, metric_type: MetricType, *args, **kwargs):
        """
        Helper method to query metrics by type.

        Args:
            request: HTTP request object
            metric_type: Type of metric (MetricType enum)

        Returns:
            Response with metric data
        """
        cluster_domain = self.get_param("cluster_domain")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        instance_role_str = self.get_param("instance_role", MetricsInstanceRole.MASTER.value)
        mode = self.get_param("mode")
        detailed = self.get_param("detailed", False)
        ip = self.get_param("ip")
        port = self.get_param("port")
        max_len_datapoints = self.get_param("max_len_datapoints")
        mermaid_format = self.get_param("mermaid_format", False)
        instance_role = MetricsInstanceRole(instance_role_str)

        result = query_redis_metrics(
            cluster_domain=cluster_domain,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
            mode=mode,
            instance_role=instance_role,
            detailed=detailed,
            ip=ip,
            port=port,
            max_len_datapoints=max_len_datapoints,
            mermaid_format=mermaid_format,
        )

        return Response(result)

    @mcp_tools_api_decorator(
        description=build_metric_description(
            metric_name="CPU usage",
            supports_info=(
                "Supports querying Redis redis_master, redis_slave or proxy, "
                "entire cluster, single machine (by IP), or single instance (by IP+port, limited metrics)."
            ),
        ),
        request_slz=RedisMetricsInputSerializer,
        response_slz=RedisMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_cpu(self, request, *args, **kwargs):
        """Query CPU usage metrics for Redis cluster"""
        return self._query_metrics_by_type(request, MetricType.CPU, *args, **kwargs)

    @mcp_tools_api_decorator(
        description=build_metric_description(
            metric_name="memory usage",
            supports_info=(
                "Supports querying Redis backends (redis_master), proxies (predixy/twemproxy), "
                "entire cluster, single machine (by IP), or single instance (by IP+port)."
            ),
        ),
        request_slz=RedisMetricsInputSerializer,
        response_slz=RedisMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_memory(self, request, *args, **kwargs):
        """Query memory usage metrics for Redis cluster"""
        return self._query_metrics_by_type(request, MetricType.MEMORY, *args, **kwargs)

    @mcp_tools_api_decorator(
        description=build_metric_description(
            metric_name="connection count",
            supports_info=(
                "Supports querying Redis backends (redis_master), proxies (predixy/twemproxy), "
                "entire cluster, single machine (by IP), or single instance (by IP+port)."
            ),
        ),
        request_slz=RedisMetricsInputSerializer,
        response_slz=RedisMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_connections(self, request, *args, **kwargs):
        """Query connection count metrics for Redis cluster"""
        return self._query_metrics_by_type(request, MetricType.CONNECTIONS, *args, **kwargs)

    @mcp_tools_api_decorator(
        description=build_metric_description(
            metric_name="QPS",
            supports_info=(
                "Supports querying proxy/redis_master. "
                "Can query entire cluster, single machine (by IP), or single instance (by IP+port)."
            ),
        ),
        request_slz=RedisMetricsInputSerializer,
        response_slz=RedisMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_qps(self, request, *args, **kwargs):
        """Query QPS metrics for Redis cluster"""
        return self._query_metrics_by_type(request, MetricType.QPS, *args, **kwargs)
