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
from typing import List, Optional

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsInstanceRole, MetricsStatsType, MetricType
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService
from backend.dbm_aiagent.mcp_tools.redis.utils import calculate_time_range_window, generate_mermaid_line_chart

logger = logging.getLogger("root")


def _query_cluster(cluster_domain: str, max_len_datapoints: int, start_time, end_time):
    """Shared preamble: resolve cluster and compute time range / window."""
    try:
        cluster = Cluster.objects.get(immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        logger.error(f"Cluster not found: {cluster_domain}")
        return None, None, None, {"error": f"Cluster not found: {cluster_domain}"}

    time_range, time_window = calculate_time_range_window(max_len_datapoints, start_time, end_time)
    return cluster, time_range, time_window, None


def query_redis_metrics_series(
    cluster_domain: str,
    metric_type: MetricType,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    instance_role: MetricsInstanceRole = MetricsInstanceRole.MASTER,
    ip: Optional[str] = None,
    port: Optional[int] = None,
    max_len_datapoints: int = 100,
    mermaid_format: bool = False,
    group_by: Optional[List[MetricsGroupBy]] = None,
) -> dict:
    """
    Query Redis cluster time-series metrics.

    Returns aggregated time series data (and optionally mermaid chart code).
    Aggregation level is determined by ip/port filters:
    - INSTANCE level: Both ip and port provided
    - MACHINE level: Only ip provided
    - CLUSTER level: No filters

    Args:
        cluster_domain: Domain name of the cluster
        metric_type: Type of metric (MetricType enum)
        start_time: Start time (datetime, optional)
        end_time: End time (datetime, optional)
        instance_role: Role of instances to query
        ip: Optional IP address filter
        port: Optional port filter (requires ip)
        max_len_datapoints: Maximum data points in series
        mermaid_format: When True, generates mermaid xychart-beta code
        group_by: Optional dimensions for grouping results

    Returns:
        Dict with:
        - series: Dict[str, List[List[float]]] time series keyed by dimension
        - mermaid_code: str (when mermaid_format=True and series exists; series is removed)
    """
    cluster, time_range, time_window, err = _query_cluster(cluster_domain, max_len_datapoints, start_time, end_time)
    if err:
        return err

    metrics_svc = RedisMetricsQueryService()
    series = metrics_svc.query_cluster_metrics(
        cluster=cluster,
        metric_type=metric_type,
        time_range=time_range,
        need_stats=False,
        need_overall=True,
        time_window=time_window,
        instance_role=instance_role,
        ip=ip,
        port=port,
        group_by=group_by,
    )

    if series is None:
        return {"error": f"Failed to query metrics for {cluster_domain}"}

    raw_series = series.raw_series or {}
    result = {"series": raw_series}

    if mermaid_format and raw_series:
        y_labels = {
            MetricType.CPU_USAGE: "%CPU",
            MetricType.MEMORY_USAGE: "%Memory",
            MetricType.IO_USAGE: "%IO",
            MetricType.DISK_USAGE: "%Disk",
            MetricType.CONNECTIONS: "Connections",
            MetricType.QPS: "Queries/sec",
            MetricType.HOST_LATENCY: "Latency (μs)",
            MetricType.COMMAND_LATENCY: "Latency (μs)",
            MetricType.LATENCY_DISTRIBUTION: "Requests",
            MetricType.CAPACITY: "Bytes",
        }

        title = f"{cluster_domain} {metric_type.value.upper()}"
        result["mermaid_code"] = generate_mermaid_line_chart(
            title=title,
            series_data=raw_series,
            y_label=y_labels.get(metric_type, "Value"),
        )
        result.pop("series")

    return result


def query_redis_metrics_stats(
    cluster_domain: str,
    metric_type: MetricType,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    instance_role: MetricsInstanceRole = MetricsInstanceRole.MASTER,
    ip: Optional[str] = None,
    port: Optional[int] = None,
    max_len_datapoints: int = 100,
    group_by: Optional[List[MetricsGroupBy]] = None,
    stats_type: MetricsStatsType = MetricsStatsType.VERTICAL,
) -> dict:
    """
    Query Redis cluster scalar statistics.

    Returns computed statistics (min, max, avg, median, p95, cv, trend, etc.).
    Aggregation level is determined by ip/port filters:
    - INSTANCE level: Both ip and port provided
    - MACHINE level: Only ip provided
    - CLUSTER level: No filters

    Args:
        cluster_domain: Domain name of the cluster
        metric_type: Type of metric (MetricType enum)
        start_time: Start time (datetime, optional)
        end_time: End time (datetime, optional)
        instance_role: Role of instances to query
        ip: Optional IP address filter
        port: Optional port filter (requires ip)
        max_len_datapoints: Maximum data points (controls PromQL time window)
        group_by: Optional dimensions for grouping results
        stats_type: VERTICAL (temporal stats on aggregated series) or
            HORIZONTAL (stats across instances per time point)

    Returns:
        Dict with:
        - statistics: Dict with scalar values or per-key statistics
    """
    cluster, time_range, time_window, err = _query_cluster(cluster_domain, max_len_datapoints, start_time, end_time)
    if err:
        return err

    is_vertical = stats_type == MetricsStatsType.VERTICAL

    metrics_svc = RedisMetricsQueryService()
    series = metrics_svc.query_cluster_metrics(
        cluster=cluster,
        metric_type=metric_type,
        time_range=time_range,
        need_stats=not is_vertical,
        need_overall=is_vertical,
        time_window=time_window,
        instance_role=instance_role,
        ip=ip,
        port=port,
        group_by=group_by,
        vertical_stats=is_vertical,
    )

    if series is None:
        return {"error": f"Failed to query metrics for {cluster_domain}"}

    statistics = series.statistics or {}
    return {"statistics": statistics}
