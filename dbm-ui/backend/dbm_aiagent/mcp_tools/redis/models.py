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

from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggregationLevel, MetricsInstanceRole, MetricType


@dataclass
class MetricsQueryParams:
    """Parameters for building metrics queries"""

    cluster_domains: List[str]  # List of cluster domain names to query
    metric_type: MetricType  # Type of metric being queried (CPU, MEMORY, etc.)
    metric_config: dict  # Configuration dict with 'data_source_key', 'over_time', etc.
    aggregation_level: MetricsAggregationLevel  # Level of aggregation (CLUSTER, MACHINE, or INSTANCE)
    time_window: int = 60  # Time window in seconds

    # Filtering options
    instance_role: Optional[MetricsInstanceRole] = None  # Role of instances to query
    ip_filter: Optional[str] = None  # Optional IP address to filter for single machine query
    port_filter: Optional[int] = None  # Optional port to filter for single instance query

    # Output options
    need_stats: bool = True  # Whether to include statistical queries
    detailed: bool = False  # When True, downgrades dimensions by one level


@dataclass
class MetricSeries:
    """
    Statistical measures and raw time series for metrics.

    This class supports three aggregation levels:
    1. INSTANCE (ip:port): Metrics for a single instance
       - raw_series: {"ip:port": [[value, timestamp], ...]}
       - Aggregated series: min/max/avg/stddev computed across the single instance's time series
       - statistics: scalar values computed from aggregated series

    2. MACHINE (ip): Metrics aggregated across all instances on one machine
       - raw_series: {"ip:port1": [...], "ip:port2": [...], ...} for all ports on that IP
       - Aggregated series: min/max/avg/stddev computed across all instances on that machine
       - statistics: scalar values computed from aggregated series

    3. CLUSTER: Metrics aggregated across all machines in the cluster
       - raw_series: {"ip1": [...], "ip2": [...], ...} for all IPs in cluster
       - Aggregated series: min/max/avg/stddev computed across all machines
       - statistics: scalar values computed from aggregated series

    When raw=False, statistics are ALWAYS scalar values:
    - min: min(min_series)
    - max: max(max_series)
    - avg: avg(avg_series)
    - stddev: stddev(max_series) - measures stability of peak values
    """

    aggregation_level: MetricsAggregationLevel
    min_series: Optional[List[List[float]]] = None
    max_series: Optional[List[List[float]]] = None
    avg_series: Optional[List[List[float]]] = None
    stddev_series: Optional[List[List[float]]] = None
    raw_series: Optional[Dict[str, List[List[float]]]] = None
