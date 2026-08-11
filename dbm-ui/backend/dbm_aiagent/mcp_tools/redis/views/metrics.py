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
from typing import List

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    auth_parse_clusters,
    auth_parse_hosts,
    auth_parse_instances,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsInstanceRole, MetricType
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_metrics import (
    query_redis_metrics_series,
    query_redis_metrics_stats,
    resolve_cluster_from_domain,
    resolve_cluster_from_instances,
    resolve_cluster_from_ip,
)
from backend.dbm_aiagent.mcp_tools.redis.models import MetricsQueryBatch
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_metrics import (
    RedisClusterBackendSeriesInputSerializer,
    RedisClusterBackendStatsInputSerializer,
    RedisClusterProxySeriesInputSerializer,
    RedisClusterProxyStatsInputSerializer,
    RedisInstanceSeriesInputSerializer,
    RedisInstanceStatsInputSerializer,
    RedisMachineSeriesInputSerializer,
    RedisMachineStatsInputSerializer,
    RedisMetricsSeriesOutputSerializer,
    RedisMetricsStatsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class RedisMetricsMcpToolsViewSet(McpToolsViewSet):
    """Redis metrics MCP tools viewset for querying cluster performance metrics"""

    default_permission_class = [DBManagePermission()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_group_by(self):
        group_by_list = self.get_param("group_by")
        if group_by_list is None:
            return []
        if not isinstance(group_by_list, list):
            group_by_list = [group_by_list]
        return [MetricsGroupBy(dim) for dim in group_by_list]

    def _do_series(
        self,
        batches: List[MetricsQueryBatch],
        time_range: tuple,
        time_window: int,
        partial_errors: list = None,
    ):
        result = query_redis_metrics_series(
            batches=batches,
            metric_type=MetricType(self.get_param("metric_type")),
            time_range=time_range,
            time_window=time_window,
            group_by=self._parse_group_by(),
            include_meta=self.get_param("include_meta", False),
        )
        if partial_errors:
            result.setdefault("partial_errors", []).extend(partial_errors)
        return Response(result)

    def _do_stats(
        self,
        batches: List[MetricsQueryBatch],
        time_range: tuple,
        time_window: int,
        partial_errors: list = None,
    ):
        result = query_redis_metrics_stats(
            batches=batches,
            metric_type=MetricType(self.get_param("metric_type")),
            time_range=time_range,
            time_window=time_window,
            group_by=self._parse_group_by(),
            include_meta=self.get_param("include_meta", False),
        )
        if partial_errors:
            result.setdefault("partial_errors", []).extend(partial_errors)
        return Response(result)

    # ------------------------------------------------------------------
    # Cluster-level: proxy
    # ------------------------------------------------------------------

    @mcp_tools_api_decorator(
        description=_(
            "Query time-series metrics for Redis cluster PROXY nodes. "
            "Applicable metrics: cpu_usage (machine-level), memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, latency_distribution (not capacity, not cpu_usage_instance). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic). "
            "Keep max_len_datapoints<=15 to avoid context length issues."
        ),
        request_slz=RedisClusterProxySeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="redis_metrics",
    )
    def query_cluster_proxy_series(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.PROXY,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_series(resolution.batches, resolution.time_range, resolution.time_window)

    @mcp_tools_api_decorator(
        description=_(
            "Query scalar statistics (min/max/avg/p95/cv/trend) for Redis cluster PROXY nodes. "
            "Applicable metrics: cpu_usage (machine-level), memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, latency_distribution (not capacity, not cpu_usage_instance). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic)."
        ),
        request_slz=RedisClusterProxyStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_cluster_proxy_stats(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.PROXY,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
            enforce_max_datapoints_limit=False,
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_stats(resolution.batches, resolution.time_range, resolution.time_window)

    # ------------------------------------------------------------------
    # Cluster-level: master
    # ------------------------------------------------------------------

    @mcp_tools_api_decorator(
        description=_(
            "Query time-series metrics for Redis cluster MASTER nodes. "
            "Applicable metrics: cpu_usage (machine-level), cpu_usage_instance (process-level, in cores), "
            "memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, capacity (not latency_distribution). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic). "
            "Keep max_len_datapoints<=15 to avoid context length issues."
        ),
        request_slz=RedisClusterBackendSeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="redis_metrics",
    )
    def query_cluster_master_series(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.MASTER,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_series(resolution.batches, resolution.time_range, resolution.time_window)

    @mcp_tools_api_decorator(
        description=_(
            "Query scalar statistics (min/max/avg/p95/cv/trend) for Redis cluster MASTER nodes. "
            "Applicable metrics: cpu_usage (machine-level), cpu_usage_instance (process-level, in cores), "
            "memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, capacity (not latency_distribution). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic)."
        ),
        request_slz=RedisClusterBackendStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_cluster_master_stats(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.MASTER,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
            enforce_max_datapoints_limit=False,
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_stats(resolution.batches, resolution.time_range, resolution.time_window)

    # ------------------------------------------------------------------
    # Cluster-level: slave
    # ------------------------------------------------------------------

    @mcp_tools_api_decorator(
        description=_(
            "Query time-series metrics for Redis cluster SLAVE nodes. "
            "Applicable metrics: cpu_usage (machine-level), cpu_usage_instance (process-level, in cores), "
            "memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, capacity (not latency_distribution). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic). "
            "Keep max_len_datapoints<=15 to avoid context length issues."
        ),
        request_slz=RedisClusterBackendSeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_cluster_slave_series(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.SLAVE,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_series(resolution.batches, resolution.time_range, resolution.time_window)

    @mcp_tools_api_decorator(
        description=_(
            "Query scalar statistics (min/max/avg/p95/cv/trend) for Redis cluster SLAVE nodes. "
            "Applicable metrics: cpu_usage (machine-level), cpu_usage_instance (process-level, in cores), "
            "memory_usage, io_usage, disk_usage, connections, qps, "
            "host_latency, command_latency, capacity (not latency_distribution). "
            "group_by: ip, instance, cluster_domain (per-command/bucket/capacity breakdowns are automatic)."
        ),
        request_slz=RedisClusterBackendStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_cluster_slave_stats(self, request, *args, **kwargs):
        cluster_domains = self.get_param("cluster_domains")
        resolution = resolve_cluster_from_domain(
            cluster_domains,
            MetricsInstanceRole.SLAVE,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
            enforce_max_datapoints_limit=False,
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_stats(resolution.batches, resolution.time_range, resolution.time_window)

    # ------------------------------------------------------------------
    # Machine-level
    # ------------------------------------------------------------------

    @mcp_tools_api_decorator(
        description=_(
            "Query time-series metrics for a specific machine (by IP). "
            "Cluster and instance role are auto-resolved. "
            "All metric types are accepted; latency_distribution is proxy-only; "
            "capacity and cpu_usage_instance are backend-only. "
            "group_by: ip, instance (not cluster_domain; per-command/bucket/capacity breakdowns are automatic). "
            "Keep max_len_datapoints<=15 to avoid context length issues."
        ),
        request_slz=RedisMachineSeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_hosts,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_machine_series(self, request, *args, **kwargs):
        ips = self.get_param("ips")
        resolution = resolve_cluster_from_ip(
            ips,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_series(
            resolution.batches, resolution.time_range, resolution.time_window, resolution.partial_errors
        )

    @mcp_tools_api_decorator(
        description=_(
            "Query scalar statistics (min/max/avg/p95/cv/trend) for a specific machine (by IP). "
            "Cluster and instance role are auto-resolved. "
            "All metric types are accepted; latency_distribution is proxy-only; "
            "capacity and cpu_usage_instance are backend-only. "
            "group_by: ip, instance (not cluster_domain; per-command/bucket/capacity breakdowns are automatic)."
        ),
        request_slz=RedisMachineStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_hosts,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_machine_stats(self, request, *args, **kwargs):
        ips = self.get_param("ips")
        resolution = resolve_cluster_from_ip(
            ips,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
            enforce_max_datapoints_limit=False,
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_stats(
            resolution.batches, resolution.time_range, resolution.time_window, resolution.partial_errors
        )

    # ------------------------------------------------------------------
    # Instance-level
    # ------------------------------------------------------------------

    @mcp_tools_api_decorator(
        description=_(
            "Query time-series metrics for a specific instance (by IP + port). "
            "Cluster and instance role are auto-resolved. "
            "Metrics: cpu_usage_instance (process-level CPU in cores, backend-only), "
            "connections, qps, host_latency, command_latency, latency_distribution (proxy), "
            "capacity (backend); machine-level resource metrics (cpu_usage/memory_usage/io_usage/disk_usage) "
            "are not available at instance scope -- use cpu_usage_instance for per-process CPU. "
            "group_by: instance (not cluster_domain or ip; per-command/bucket/capacity breakdowns are automatic). "
            "Keep max_len_datapoints<=15 to avoid context length issues."
        ),
        request_slz=RedisInstanceSeriesInputSerializer,
        response_slz=RedisMetricsSeriesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_instance_series(self, request, *args, **kwargs):
        instances = self.get_param("instances")
        resolution = resolve_cluster_from_instances(
            instances,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_series(
            resolution.batches, resolution.time_range, resolution.time_window, resolution.partial_errors
        )

    @mcp_tools_api_decorator(
        description=_(
            "Query scalar statistics (min/max/avg/p95/cv/trend) for a specific instance (by IP + port). "
            "Cluster and instance role are auto-resolved. "
            "Metrics: cpu_usage_instance (process-level CPU in cores, backend-only), "
            "connections, qps, host_latency, command_latency, latency_distribution (proxy), "
            "capacity (backend); machine-level resource metrics (cpu_usage/memory_usage/io_usage/disk_usage) "
            "are not available at instance scope -- use cpu_usage_instance for per-process CPU. "
            "group_by: instance (not cluster_domain or ip; per-command/bucket/capacity breakdowns are automatic)."
        ),
        request_slz=RedisInstanceStatsInputSerializer,
        response_slz=RedisMetricsStatsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_METRICS],
        name_prefix="redis_metrics",
    )
    def query_instance_stats(self, request, *args, **kwargs):
        instances = self.get_param("instances")
        resolution = resolve_cluster_from_instances(
            instances,
            self.get_param("max_len_datapoints"),
            self.get_param("start_time"),
            self.get_param("end_time"),
            enforce_max_datapoints_limit=False,
        )
        if resolution.error:
            return Response(resolution.error)
        return self._do_stats(
            resolution.batches, resolution.time_range, resolution.time_window, resolution.partial_errors
        )
