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
from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.redis.enums import (
    MetricsAggregationLevel,
    MetricsGroupBy,
    MetricsInstanceRole,
    MetricType,
)


@dataclass
class InstanceFilter:
    ip: str
    port: int


@dataclass
class MetricsQueryBatch:
    """Caller/impl-layer batch: groups resolved clusters by instance_role for iterative querying.

    Each batch carries the cluster objects, their shared role, and optional scope filters
    (ip_filters for machine-level, instance_filters for instance-level).  entity_meta is
    populated during resolution so the caller can optionally include it in the API response.
    """

    clusters: List[Cluster]
    instance_role: MetricsInstanceRole
    ip_filters: Optional[List[str]] = None
    instance_filters: Optional[List[InstanceFilter]] = None
    entity_meta: Optional[Dict[str, dict]] = None


@dataclass
class MetricsQueryParams:
    """Service-layer params: fully-resolved inputs for building PromQL queries.

    Constructed inside RedisMetricsQueryService.query_metrics() from caller-supplied
    arguments plus internally resolved values (metric_config, aggregation_level).
    """

    cluster_domains: Optional[List[str]]  # Optional list of cluster domain names to query
    metric_type: MetricType  # Type of metric being queried (CPU, MEMORY, etc.)
    metric_config: dict  # Configuration dict with template-based PromQL config
    aggregation_level: MetricsAggregationLevel  # Level of aggregation (CLUSTER, MACHINE, or INSTANCE)
    time_window: int = 60  # Time window in seconds

    # Filtering options
    instance_role: Optional[MetricsInstanceRole] = None  # Role of instances to query
    ip_filters: Optional[List[str]] = None  # Optional IP list filter (machine scope)
    instance_filters: Optional[List[InstanceFilter]] = None  # Optional ip:port pair filter (instance scope)

    # Output options
    need_stats: bool = True  # Whether to include statistical queries
    need_overall: bool = True  # Whether to include overall time series queries
    group_by: Optional[
        List[MetricsGroupBy]
    ] = None  # Explicit dimensions for grouping results (e.g., [cluster_domain, ip, port])


@dataclass
class MetricSeries:
    """
    Statistical measures and raw time series for metrics.

    This class supports three aggregation levels:
    1. INSTANCE (ip:port): Metrics for a single instance
       - raw_series: {"ip:port": [[value, timestamp], ...]}
       - stats_series_by_key: {"ip:port": {MIN: [...], MAX: [...], AVG: [...], STDDEV: [...]}}
         (Inner dict keys are MetricsAggFunction enum values)
       - statistics: scalar values computed from stats_series_by_key

    2. MACHINE (ip): Metrics aggregated across all instances on one machine
       - raw_series: {"ip:port1": [...], "ip:port2": [...], ...} for all ports on that IP
       - stats_series_by_key: {"ip": {MIN: [...], MAX: [...], AVG: [...], STDDEV: [...]}}
       - statistics: scalar values computed from stats_series_by_key

    3. CLUSTER: Metrics aggregated across all machines in the cluster
       - raw_series: {"ip1": [...], "ip2": [...], ...} for all IPs in cluster
       - stats_series_by_key: {"cluster_domain": {MIN: [...], MAX: [...], AVG: [...], STDDEV: [...]}}
       - statistics: scalar values computed from stats_series_by_key

    Statistics are computed from stats_series_by_key:
    - For each key in stats_series_by_key, statistics are calculated from the respective series
    - min: min(values) from stats_series_by_key[key][MetricsAggFunction.MIN]
    - max: max(values) from stats_series_by_key[key][MetricsAggFunction.MAX]
    - avg: average(values) from stats_series_by_key[key][MetricsAggFunction.AVG]
    - stddev: max(values) from stats_series_by_key[key][MetricsAggFunction.STDDEV] (represents peak variability)
    - median, p95, cv, trend: calculated from stats_series_by_key[key][MetricsAggFunction.AVG]
    """

    aggregation_level: MetricsAggregationLevel
    raw_series: Optional[Dict[str, List[List[float]]]] = None
    stats_series_by_key: Optional[Dict[str, Dict[str, List[List[float]]]]] = None
    statistics: Optional[Dict[str, Dict[str, float]]] = None
