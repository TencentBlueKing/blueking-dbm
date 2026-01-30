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
from datetime import datetime
from typing import Optional

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsInstanceRole, MetricsOutputMode, MetricType
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService
from backend.dbm_aiagent.mcp_tools.redis.utils import calculate_time_range_window, generate_mermaid_line_chart

logger = logging.getLogger("root")


def query_redis_metrics(
    cluster_domain: str,
    metric_type: MetricType,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    mode: str = MetricsOutputMode.STATS.value,
    instance_role: MetricsInstanceRole = MetricsInstanceRole.MASTER,
    detailed: bool = False,
    ip: Optional[str] = None,
    port: Optional[int] = None,
    max_len_datapoints: int = 100,
    mermaid_format: bool = False,
) -> dict:
    """
    Query Redis cluster metrics for MCP tools with explicit aggregation levels.

    This is the main entry point for querying Redis metrics from MCP tools.
    It automatically determines the aggregation level based on provided filters:
    - INSTANCE level: Both ip and port provided (single instance)
    - MACHINE level: Only ip provided (all instances on one machine)
    - CLUSTER level: No filters (all machines in cluster)

    Args:
        cluster_domain: Domain name of the cluster
        metric_type: Type of metric (MetricType enum)
        start_time: Start time (datetime object from serializer optional)
        end_time: End time (datetime object from serializer optional)
        mode: Output mode - "overall" (only aggregated series), "stats" (only statistics), "both" (both)
        instance_role: Role of instances to query (InstanceRole enum)
        detailed: When True, downgrades aggregation dimensions by one level
        ip: Optional IP address to filter for machine/instance level query
        port: Optional port to filter for instance level query (requires ip)
        max_len_datapoints: The maximum of items in series to return
        mermaid_format: When True and series data exists, generates mermaid xychart-beta code

    Returns:
        Dict with metric data matching RedisMetricsOutputSerializer format:

        Common fields for all responses:
        - cluster_domain: str
        - metric_type: str
        - instance_role: str
        - aggregation_level: "instance" | "machine" | "cluster"
        - ip: str (if filtered)
        - port: int (if filtered)
        - mode: str

        When mode="overall" or mode="both":
        - series: Dict[str, List[List[float]]]
          * INSTANCE: {"ip:port": [[value, timestamp], ...]} # Not all metrics are instance-wise
          * MACHINE: {"ip": [...]} or with detailed=True: {"ip:port1": [...], "ip:port2": [...]}
          * CLUSTER: {"cluster_domain": [...]} or with detailed=True: {"ip1": [...], "ip2": [...]}

        When mode="stats" or mode="both":
        - statistics: Dict with scalar values or per-key statistics
          * When detailed=False (default): Aggregated cluster-level statistics
            {
              "min": float,      # Minimum value
              "max": float,      # Maximum value
              "avg": float,      # Average value
              "median": float,   # Median value (less affected by outliers)
              "p95": float,      # 95th percentile (typical worst case)
              "cv": float,       # Coefficient of variation (%) - normalized variability
              "trend": float     # Linear trend slope (positive=increasing, negative=decreasing)
            }
          * When detailed=True: Per-key statistics matching series structure
            {
              "ip1": {"min": float, "max": float, "avg": float, ...},
              "ip2": {"min": float, "max": float, "avg": float, ...},
              ...
            }
            or for machine-level with detailed=True:
            {
              "ip:port1": {"min": float, "max": float, "avg": float, ...},
              "ip:port2": {"min": float, "max": float, "avg": float, ...},
              ...
            }
          * Computed from aggregated time series (when detailed=False):
            - min: min(min_series)
            - max: max(max_series)
            - avg: avg(avg_series)
            - median: median(avg_series)
            - p95: 95th percentile(avg_series)
            - cv: (stddev/avg)*100 from avg_series
            - trend: linear regression slope from avg_series
          * Computed from raw_series per key (when detailed=True):
            - Each key's statistics computed from its individual time series

        When mermaid_format=True and series data exists:
        - mermaid_code: str (pre-formatted mermaid xychart-beta code ready to render)
    """
    try:
        cluster = Cluster.objects.get(immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        logger.error(f"Cluster not found: {cluster_domain}")
        return {"error": f"Cluster not found: {cluster_domain}"}

    time_range, time_window = calculate_time_range_window(max_len_datapoints, start_time, end_time)

    # Query metrics with optional filters
    metrics_svc = RedisMetricsQueryService()
    series, params = metrics_svc.query_cluster_metrics(
        cluster=cluster,
        metric_type=metric_type,
        time_range=time_range,
        time_window=time_window,
        mode=mode,
        instance_role=instance_role,
        detailed=detailed,
        ip=ip,
        port=port,
    )

    base_response = {"query_params": params}

    # Format response based on mode
    result = None
    match mode:
        case MetricsOutputMode.OVERALL.value:
            result = {
                **base_response,
                "series": series.raw_series or {},
            }
        case MetricsOutputMode.STATS.value:
            if detailed and series.raw_series:
                scalar_stats = metrics_svc.compute_per_key_stats_from_raw_series(series)
            else:
                scalar_stats = metrics_svc.compute_scalar_stats_from_series(series)
            result = {
                **base_response,
                "statistics": scalar_stats,
            }
        case MetricsOutputMode.BOTH.value:
            if detailed and series.raw_series:
                scalar_stats = metrics_svc.compute_per_key_stats_from_raw_series(series)
            else:
                scalar_stats = metrics_svc.compute_scalar_stats_from_series(series)
            result = {
                **base_response,
                "series": series.raw_series or {},
                "statistics": scalar_stats,
            }
        case _:
            result = {**base_response, "error": f"Invalid mode: {mode}. Must be 'overall', 'stats', or 'both'"}

    if not result:
        return {"error": f"Failed to query metrics for {cluster_domain}"}

    # Generate mermaid chart if requested and series data exists
    if mermaid_format and "series" in result and result["series"]:
        # Determine y-axis label based on metric type
        y_labels = {
            MetricType.CPU: "%CPU",
            MetricType.MEMORY: "%Memory",
            MetricType.CONNECTIONS: "Connections",
            MetricType.QPS: "Queries/sec",
        }

        title = f"{cluster_domain} {metric_type.value.upper()}"

        result["mermaid_code"] = generate_mermaid_line_chart(
            title=title,
            series_data=result["series"],
            y_label=y_labels.get(metric_type, "Value"),
        )
        result.pop("series")

    return result
