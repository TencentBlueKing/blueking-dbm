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
    # unify_query step/interval (seconds) between returned points. Not PromQL lookback.
    time_window: int = 60

    # Filtering options
    instance_role: Optional[MetricsInstanceRole] = None  # Role of instances to query
    ip_filters: Optional[List[str]] = None  # Optional IP list filter (machine scope)
    instance_filters: Optional[List[InstanceFilter]] = None  # Optional ip:port pair filter (instance scope)

    # Output options
    group_by: Optional[
        List[MetricsGroupBy]
    ] = None  # Explicit dimensions for grouping results (e.g., [cluster_domain, ip, port])


@dataclass
class MetricSeries:
    """
    Raw time series and the timeline statistics derived from them.

    ``raw_series`` maps a result key to its [[value, timestamp], ...] points. The key is composed of
    the metric's intrinsic breakdown values (cmd / latency bucket / capacity sub-type) and the scope
    identifier, depending on aggregation level:
    1. INSTANCE (ip:port): keyed by intrinsic breakdown, or "ip:port" when none.
    2. MACHINE (ip): one entry per instance/breakdown on that machine.
    3. CLUSTER: one entry per group_by/breakdown dimension value across the cluster.

    ``statistics`` holds scalar timeline stats per ``raw_series`` key (min, max, avg, median, p95,
    cv, trend, latest), computed over each series' values across the time window.
    """

    aggregation_level: MetricsAggregationLevel
    raw_series: Optional[Dict[str, List[List[float]]]] = None
    statistics: Optional[Dict[str, Dict[str, float]]] = None
