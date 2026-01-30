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
import copy
import logging
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.redis.constants import METRICS_CONFIG_MAP, PROMQL_TEMPLATE, UNIFY_QUERY_PARAMS
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggFunction as AggFunction
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggregationLevel as AggregationLevel
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsInstanceRole as InstanceRole
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsOutputMode as OutputMode
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricType
from backend.dbm_aiagent.mcp_tools.redis.models import MetricSeries, MetricsQueryParams
from backend.dbm_aiagent.mcp_tools.redis.utils import get_metric_key

logger = logging.getLogger("root")


class RedisMetricsQueryService:
    """
    Service class for querying Redis metrics.

    This class encapsulates the logic for:
    - Building PromQL queries for various metrics (CPU, memory, connections, QPS)
    - Querying BKMonitor API with batch optimization
    - Parsing responses into structured data
    """

    def __init__(self):
        """Initialize the metrics service"""
        pass

    def _build_queries(self, params: MetricsQueryParams) -> List[dict]:
        """
        Build multiple PromQL queries for all statistical metrics.

        The key is to apply statistical aggregations (min, max, avg, stddev)
        to the per-machine time series, NOT to an already-aggregated query.

        Strategy:
        1. Get per-machine time series with over_time function
        2. Apply statistical aggregation by cluster_domain
        3. Support filtering by IP and/or port for single machine/instance queries

        Args:
            params: MetricsQueryParams object containing all query parameters

        Returns:
            List of query configs for unify_query API
        """
        # Build regex pattern for all clusters
        cluster_regex = "|".join(params.cluster_domains)

        # Determine aggregation parameters based on metric config
        scale_factor = params.metric_config.get("scale_factor")
        data_source_key = params.metric_config.get("data_source_key")

        # Determine aggregation function - use metric config if specified, otherwise default by type
        agg_func = params.metric_config.get("agg_func")
        if not agg_func:
            if params.metric_type in (MetricType.CPU, MetricType.MEMORY, MetricType.CONNECTIONS):
                agg_func = AggFunction.MAX
            elif params.metric_type == MetricType.QPS:
                agg_func = AggFunction.SUM
            else:
                agg_func = AggFunction.MAX  # Default fallback

        # Determine dimensions based on aggregation level and detailed flag
        # When detailed=True, downgrade dimensions by one level
        if params.aggregation_level == AggregationLevel.CLUSTER:
            raw_dimensions = "cluster_domain,ip" if params.detailed else "cluster_domain"
        elif params.aggregation_level == AggregationLevel.MACHINE:
            raw_dimensions = "cluster_domain,ip,port" if params.detailed else "cluster_domain,ip"
        else:  # INSTANCE
            # Instance level is already most detailed, no downgrade
            raw_dimensions = "cluster_domain,ip,port"

        # Build extra labels for filtering
        extra_labels = []
        if params.instance_role:
            extra_labels.append(f'instance_role="{params.instance_role.value}"')
        if params.ip_filter:
            extra_labels.append(f'ip="{params.ip_filter}"')
        if params.port_filter:
            extra_labels.append(f'instance_port="{params.port_filter}"')

        extra_labels_str = "," + ",".join(extra_labels) if extra_labels else ""

        # Build base metric selector using unified template
        base_metric_selector = PROMQL_TEMPLATE.format(
            func=agg_func.value,
            dimensions=raw_dimensions,
            over_time=params.metric_config["over_time"],
            data_source_key=data_source_key,
            cluster_domains=cluster_regex,
            extra_labels=extra_labels_str,
            time_window=params.time_window,
        )

        # Apply scale factor if needed (e.g., for twemproxy CPU)
        if scale_factor:
            base_metric_selector = f"({base_metric_selector})/{scale_factor}"

        # Build statistical aggregation queries with cluster-level dimensions
        queries = (
            [
                {
                    "data_source_label": "prometheus",
                    "data_type_label": "time_series",
                    "promql": (
                        f"label_replace({func.value} by (cluster_domain) ({base_metric_selector}), "
                        f'"query_type", "{func.value}", "", "")'
                    ),
                    "interval": params.time_window,
                    "alias": func.value,
                }
                for func in [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV]
            ]
            if params.need_stats
            else []
        )

        # Build overall data query - preserves dimensions based on aggregation level and detailed flag
        overall_selector = base_metric_selector
        queries.append(
            {
                "data_source_label": "prometheus",
                "data_type_label": "time_series",
                "promql": f'label_replace({overall_selector}, "query_type", "overall", "", "")',
                "interval": params.time_window,
                "alias": "a",
            }
        )

        return queries

    def _build_query_params(
        self,
        query_configs: List[dict],
        time_range: Tuple[int, int],
    ) -> dict:
        """
        Prepare query parameters for BKMonitor unify_query API.

        Args:
            query_configs: List of query configurations
            time_range: Tuple of (start_time, end_time) in Unix timestamp

        Returns:
            Dict of parameters ready for unify_query API
        """
        params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        params["query_configs"] = query_configs
        params["start_time"] = time_range[0]
        params["end_time"] = time_range[1]

        return params

    def _determine_aggregation_level(
        self,
        ip: Optional[str] = None,
        port: Optional[int] = None,
    ) -> AggregationLevel:
        """
        Determine the aggregation level based on provided filters.

        Args:
            ip: Optional IP address filter
            port: Optional port filter

        Returns:
            AggregationLevel enum value
        """
        if ip and port:
            return AggregationLevel.INSTANCE
        elif ip:
            return AggregationLevel.MACHINE

        return AggregationLevel.CLUSTER

    def compute_scalar_stats_from_series(self, series: MetricSeries) -> Dict[str, float]:
        """
        Compute scalar statistics from aggregated time series.

        This implements the formula:
        - min: min(min_series)
        - max: max(max_series)
        - avg: avg(avg_series)
        - median: median(avg_series) - middle value, less affected by outliers
        - p95: 95th percentile(avg_series) - typical worst case performance
        - cv: coefficient of variation(avg_series) - normalized variability measure (%)
        - trend: linear trend slope(avg_series) - positive=increasing, negative=decreasing

        Args:
            series: MetricSeries object containing min_series, max_series, and avg_series

        Returns:
            Dict with min, max, avg, median, p95, cv, trend as scalar values
        """
        result = {"min": 0.0, "max": 0.0, "avg": 0.0, "median": 0.0, "p95": 0.0, "cv": 0.0, "trend": 0.0}

        # min: min(min_series)
        if series.min_series:
            min_values = [point[0] for point in series.min_series if point[0] is not None]
            if min_values:
                result["min"] = round(min(min_values), 2)

        # max: max(max_series)
        if series.max_series:
            max_values = [point[0] for point in series.max_series if point[0] is not None]
            if max_values:
                result["max"] = round(max(max_values), 2)

        # avg, median, p95, cv, trend: computed from avg_series
        if series.avg_series:
            avg_values = [point[0] for point in series.avg_series if point[0] is not None]
            if avg_values:
                mean_val = statistics.mean(avg_values)
                result["avg"] = round(mean_val, 2)
                result["median"] = round(statistics.median(avg_values), 2)

                # p95: 95th percentile - typical worst case
                if len(avg_values) >= 20:
                    result["p95"] = round(statistics.quantiles(avg_values, n=100)[94], 2)
                else:
                    # For small samples, use a simpler approximation
                    sorted_vals = sorted(avg_values)
                    p95_idx = int(len(sorted_vals) * 0.95)
                    result["p95"] = round(sorted_vals[min(p95_idx, len(sorted_vals) - 1)], 2)

                # cv: coefficient of variation - normalized variability (%)
                if mean_val > 0 and len(avg_values) > 1:
                    stddev = statistics.stdev(avg_values)
                    result["cv"] = round((stddev / mean_val) * 100, 2)

                # trend: linear regression slope
                if len(avg_values) > 1:
                    result["trend"] = round(self._calculate_trend(series.avg_series), 4)

        return result

    def compute_per_key_stats_from_raw_series(self, series: MetricSeries) -> Dict[str, Dict[str, float]]:
        """
        Compute statistics for each series key from raw_series data.

        This is used when detailed=True to provide per-key statistics
        (e.g., per-IP or per-instance statistics) instead of aggregated cluster-level stats.

        Args:
            series: MetricSeries object containing raw_series data

        Returns:
            Dict mapping series keys to their statistics
            Example: {"ip1": {"min": 10.5, "max": 50.2, ...}, "ip2": {...}}
        """
        if not series.raw_series:
            return {}

        per_key_stats = {}
        for key, datapoints in series.raw_series.items():
            if not datapoints:
                continue

            # Extract values from datapoints
            values = [point[0] for point in datapoints if point[0] is not None]
            if not values:
                continue

            # Compute statistics for this key
            stats = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(statistics.mean(values), 2),
                "median": round(statistics.median(values), 2),
                "p95": 0.0,
                "cv": 0.0,
                "trend": 0.0,
            }

            # p95: 95th percentile
            if len(values) >= 20:
                stats["p95"] = round(statistics.quantiles(values, n=100)[94], 2)
            else:
                sorted_vals = sorted(values)
                p95_idx = int(len(sorted_vals) * 0.95)
                stats["p95"] = round(sorted_vals[min(p95_idx, len(sorted_vals) - 1)], 2)

            # cv: coefficient of variation
            mean_val = stats["avg"]
            if mean_val > 0 and len(values) > 1:
                stddev = statistics.stdev(values)
                stats["cv"] = round((stddev / mean_val) * 100, 2)

            # trend: linear regression slope
            if len(values) > 1:
                stats["trend"] = round(self._calculate_trend(datapoints), 4)

            per_key_stats[key] = stats

        return per_key_stats

    def _calculate_trend(self, series: List[List[float]]) -> float:
        """
        Calculate linear trend (slope) from time series data.

        Uses simple linear regression: y = mx + b, returns m (slope)
        Positive slope = increasing trend, negative = decreasing trend

        Args:
            series: Time series data [[value, timestamp], ...]

        Returns:
            Slope value (trend direction and magnitude)
        """
        if not series or len(series) < 2:
            return 0.0

        # Extract values and create x indices
        points = [(i, point[0]) for i, point in enumerate(series) if point[0] is not None]
        if len(points) < 2:
            return 0.0

        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_x2 = sum(p[0] ** 2 for p in points)

        # Calculate slope: m = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        denominator = n * sum_x2 - sum_x**2
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    @staticmethod
    def normalize_timestamps(datapoints: List[List[float]]) -> List[List[float]]:
        if not datapoints:
            return datapoints

        for point in datapoints:
            point[1] = point[1] / 1000

        return datapoints

    def _parse_response(
        self,
        response: dict,
        aggregation_level: AggregationLevel = AggregationLevel.CLUSTER,
    ) -> Dict[str, MetricSeries]:
        """
        Parse the unify_query response into MetricSeries per cluster.

        The API returns series in the SAME ORDER as query_configs.
        We match series to statistics by their position in the response.

        Args:
            response: Response from BKMonitor unify_query API
            aggregation_level: The level of aggregation being performed

        Returns:
            Dict mapping cluster_domain to MetricSeries
        """
        series_by_cluster = defaultdict(lambda: MetricSeries(aggregation_level=aggregation_level))
        series_list = response.get("series", [])

        for series in series_list:
            dimensions = series["dimensions"]

            cluster_domain = dimensions["cluster_domain"]
            query_type = dimensions["query_type"]

            datapoints = self.normalize_timestamps(series["datapoints"])

            if query_type == "min":
                series_by_cluster[cluster_domain].min_series = datapoints
            elif query_type == "max":
                series_by_cluster[cluster_domain].max_series = datapoints
            elif query_type == "avg":
                series_by_cluster[cluster_domain].avg_series = datapoints
            elif query_type == "stddev":
                series_by_cluster[cluster_domain].stddev_series = datapoints
            elif query_type == "overall":
                # Build key based on aggregation level and available dimensions
                if not series_by_cluster[cluster_domain].raw_series:
                    series_by_cluster[cluster_domain].raw_series = {}

                # Determine key based on available dimensions in response
                # The dimensions depend on the query (which considers detailed flag)
                ip = dimensions.get("ip")
                port = dimensions.get("port") or dimensions.get("instance_port")

                if port and ip:
                    # Most detailed: ip:port
                    key_value = f"{ip}:{port}"
                elif ip:
                    # Medium detail: ip only
                    key_value = ip
                else:
                    # Least detail: cluster_domain only
                    key_value = cluster_domain

                series_by_cluster[cluster_domain].raw_series[key_value] = datapoints
            else:
                logger.warning(f"Unknown query_type: {query_type}")

        return dict(series_by_cluster)

    def query_cluster_metrics(
        self,
        cluster: Cluster,
        metric_type: MetricType,
        mode: str,
        time_range: Tuple[int, int],
        time_window: int = 60,
        instance_role: InstanceRole = InstanceRole.MASTER,
        detailed: bool = False,
        ip: Optional[str] = None,
        port: Optional[int] = None,
    ) -> Tuple[MetricSeries, dict]:
        """
        Query metrics for a single cluster, with optional filtering by machine/instance.

        Args:
            cluster: Cluster object
            metric_type: Type of metric (MetricType enum)
            mode: Output mode - "overall" (only aggregated series), "stats" (only statistics), "both" (both)
            time_range: Tuple of (start_time, end_time) in Unix timestamp
            time_window: Time window in seconds
            instance_role: Role of instances to query (InstanceRole enum)
            detailed: When True, downgrades aggregation dimensions by one level
            ip: Optional IP address to filter for single machine query
            port: Optional port to filter for single instance query

        Returns:
            Tuple of (MetricSeries, query_params dict, detailed flag), or None if query fails
        """
        # Get metric config using dynamic lookup function
        metric_key = get_metric_key(cluster.cluster_type, metric_type, instance_role)
        if not metric_key:
            logger.error(
                f"No metric mapping found for cluster_type={cluster.cluster_type}, "
                f"metric_type={metric_type.value}, instance_role={instance_role.value}"
            )
            return None

        metric_config = METRICS_CONFIG_MAP.get(metric_key)
        if not metric_config:
            logger.error(f"No metric config found for metric_key={metric_key}")
            return None

        # Determine aggregation level
        aggregation_level = self._determine_aggregation_level(ip, port)

        # Build query parameters object
        need_stats = (
            mode != OutputMode.OVERALL.value or detailed
        )  # If detailed, we need raw series for structured `stats`
        query_params = MetricsQueryParams(
            cluster_domains=[cluster.immute_domain],
            metric_type=metric_type,
            metric_config=metric_config,
            aggregation_level=aggregation_level,
            time_window=time_window,
            instance_role=instance_role,
            ip_filter=ip,
            port_filter=port,
            need_stats=need_stats,
            detailed=detailed,
        )

        # Build all query configs
        query_configs = self._build_queries(query_params)
        params = self._build_query_params(query_configs, time_range)

        logger.info(
            f"Querying {metric_type} metrics for cluster {cluster.immute_domain} "
            f"(role={instance_role}, ip={ip}, port={port}) "
            f"with {len(query_configs)} query configs"
        )

        try:
            response = BKMonitorV3Api.unify_query(params)
        except Exception as e:
            logger.error(f"Failed to query metrics for {cluster.immute_domain}: {e}")
            return None

        # Parse response with aggregation level
        series_by_cluster = self._parse_response(response, aggregation_level)
        series = series_by_cluster.get(cluster.immute_domain)

        return series, params
