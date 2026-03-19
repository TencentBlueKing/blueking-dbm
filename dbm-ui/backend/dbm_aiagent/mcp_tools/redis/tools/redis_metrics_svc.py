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
import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.redis.constants import (
    METRIC_REGISTRY,
    METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS,
    METRICS_MAX_QUERY_RANGE_SECONDS,
    METRICS_QUERY_MAX_ATTEMPTS,
    METRICS_QUERY_RETRY_DELAY_SEC,
    TREND_UNIT_BY_METRIC_KEY,
    UNIFY_QUERY_PARAMS,
)
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggFunction as AggFunction
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggregationLevel as AggregationLevel
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsInstanceRole as InstanceRole
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricType
from backend.dbm_aiagent.mcp_tools.redis.models import InstanceFilter, MetricSeries, MetricsQueryParams
from backend.dbm_aiagent.mcp_tools.redis.utils import resolve_metric_key

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

    @staticmethod
    def _escape_promql_regex_literal(value: str) -> str:
        """
        Escape regex metacharacters for PromQL regex string literals without backslashes.

        PromQL parser may reject escapes like '\\.' in string literals. We encode metacharacters
        as single-character character classes (e.g. '.' -> '[.]') to preserve literal matching.
        """
        meta_map = {
            ".": "[.]",
            "-": "[-]",
            "+": "[+]",
            "*": "[*]",
            "?": "[?]",
            "(": "[(]",
            ")": "[)]",
            "[": "[[]",
            "]": "[]]",
            "{": "[{]",
            "}": "[}]",
            "^": "[^]",
            "$": "[$]",
            "|": "[|]",
            "\\": "[\\\\]",
        }
        return "".join(meta_map.get(ch, ch) for ch in value)

    @staticmethod
    def _build_label_matcher(label: str, values: Optional[List[Union[str, int]]]) -> Optional[str]:
        if not values:
            return None
        normalized = [str(value) for value in values if value is not None and str(value) != ""]
        if not normalized:
            return None
        if len(normalized) == 1:
            return f'{label}="{normalized[0]}"'
        escaped = "|".join(RedisMetricsQueryService._escape_promql_regex_literal(value) for value in normalized)
        return f'{label}=~"{escaped}"'

    def _build_filters_string(self, params: MetricsQueryParams) -> str:
        """Build filter string for PromQL queries"""
        filters = []
        if params.cluster_domains:
            escaped_domains = "|".join(
                self._escape_promql_regex_literal(str(domain)) for domain in params.cluster_domains if domain
            )
            if escaped_domains:
                filters.append(f'cluster_domain=~"{escaped_domains}"')
        if params.instance_role:
            filters.append(f'instance_role="{params.instance_role.value}"')
        if params.instance_filters:
            if len(params.instance_filters) != 1:
                raise ValueError("instance_filters must contain exactly one pair when building a single PromQL")
            pair = params.instance_filters[0]
            filter_mode = params.metric_config.get("instance_filter_mode", "ip_port")
            if filter_mode == "instance_label":
                filters.append(f'instance="{pair.ip}:{pair.port}"')
            else:
                filters.append(f'ip="{pair.ip}"')
                filters.append(f'instance_port="{pair.port}"')
        ip_matcher = self._build_label_matcher("ip", params.ip_filters)
        if ip_matcher:
            filters.append(ip_matcher)
        return ",".join(filters)

    def _resolve_inner_dimensions(self, params: MetricsQueryParams) -> str:
        """
        Resolve dimensions for the inner/base PromQL query.

        Base dimensions are scope-aware:
        - cluster scope: cluster_domain
        - machine scope: ip
        - instance scope: ip,instance_port

        Metric-required dimensions are then merged on top.

        Args:
            params: MetricsQueryParams object

        Returns:
            Comma-separated dimensions string for inner query
        """
        required_dimensions = params.metric_config.get("required_dimensions", [])

        if params.aggregation_level == AggregationLevel.MACHINE:
            dimensions = ["ip"]
        elif params.aggregation_level == AggregationLevel.INSTANCE:
            dimensions = ["ip", "instance_port"]
        else:
            dimensions = ["cluster_domain"]

        # Add required dimensions from metric config
        for req_dim in required_dimensions:
            if req_dim not in dimensions:
                dimensions.append(req_dim)

        return ",".join(dimensions)

    def _resolve_outer_dimensions(self, params: MetricsQueryParams) -> str:
        """
        Resolve dimensions for the outer aggregation query.

        The outer query wraps the inner query and uses dimensions based on the user's
        group_by parameter. This allows users to choose their desired aggregation level.

        Args:
            params: MetricsQueryParams object

        Returns:
            Comma-separated dimensions string for outer aggregation (e.g., "cluster_domain" or "cluster_domain,ip,port")

        Raises:
            ValueError: If any group_by dimension is not in supported_group_by list
        """
        group_by_list = params.group_by
        supported_group_by = params.metric_config.get("supported_group_by", [])

        # Scope-first defaults when group_by is omitted
        if not group_by_list:
            if params.aggregation_level == AggregationLevel.MACHINE:
                return "ip"
            if params.aggregation_level == AggregationLevel.INSTANCE:
                return "ip,instance_port"
            return "cluster_domain"

        # Start with cluster_domain for explicit group_by behavior
        dimensions = ["cluster_domain"]

        # Validate and add each group_by dimension
        for group_by in group_by_list:
            group_by_value = group_by.value

            # Validate against supported options (direct enum comparison)
            if group_by not in supported_group_by:
                supported_values = [g.value for g in supported_group_by]
                raise ValueError(
                    f"group_by '{group_by_value}' not supported for this metric. "
                    f"Supported options: {supported_values}"
                )

            # Map enum to actual dimension name and add if not already present
            if group_by == MetricsGroupBy.IP:
                if "ip" not in dimensions:
                    dimensions.append("ip")
            elif group_by == MetricsGroupBy.INSTANCE:
                if "ip" not in dimensions or "instance_port" not in dimensions:
                    to_move = ["ip", "instance_port"]
                    dimensions = [d for d in dimensions if d not in to_move] + to_move
            elif group_by == MetricsGroupBy.CMD:
                if "cmd" not in dimensions:
                    dimensions.append("cmd")
            elif group_by == MetricsGroupBy.BUCKET:
                if "bucket_label" not in dimensions:
                    dimensions.append("bucket_label")
            elif group_by == MetricsGroupBy.CLUSTER_DOMAIN:
                # cluster_domain is already in dimensions, skip
                pass

        return ",".join(dimensions)

    def _parse_query_type(self, query_type: str) -> Optional[AggFunction]:
        try:
            return AggFunction(query_type)
        except (ValueError, KeyError):
            return None

    def _prepare_query_context(
        self, params: MetricsQueryParams
    ) -> Tuple[str, str, str, AggFunction, List[AggFunction]]:
        """
        Prepare shared query context used across query builders.

        Returns:
            Tuple of (inner_dims, outer_dims, filters_str, overall_agg, stats_aggs)
            - inner_dims: Comma-separated dimensions for inner query
            - outer_dims: Comma-separated dimensions for outer aggregation
            - filters_str: Filter string for PromQL queries
            - overall_agg: AggFunction enum value for overall aggregation (e.g., AggFunction.MAX, AggFunction.SUM)
            - stats_aggs: List of AggFunction enum values for stats aggregation (e.g., [AggFunction.MIN, AggFunction.MAX])
        """
        inner_dims = self._resolve_inner_dimensions(params)
        outer_dims = self._resolve_outer_dimensions(params)
        filters_str = self._build_filters_string(params)
        aggregation = params.metric_config.get("aggregation", {})
        overall_agg = aggregation.get("overall", AggFunction.SUM)
        stats_aggs = aggregation.get("stats", [])
        return inner_dims, outer_dims, filters_str, overall_agg, stats_aggs

    def _build_bucket_queries(
        self, params: MetricsQueryParams, buckets: List[dict]
    ) -> Tuple[List[dict], Optional[str]]:
        """
        Build queries for bucket-based metrics (e.g., latency distribution).

        Uses two-level aggregation:
        - Inner query: Uses inner_dimensions (cluster_domain + required_dimensions)
        - Outer aggregation: Wraps inner query with outer_dimensions (based on user's group_by)

        Args:
            params: MetricsQueryParams object
            buckets: List of bucket definitions with le_upper, le_lower, and label

        Returns:
            Tuple of (List of query configs, None)
        """
        query_configs = []
        inner_dims, outer_dims, filters_str, overall_agg, stats_aggs = self._prepare_query_context(params)

        promql_parts = params.metric_config.get("promql_parts", {})
        if not promql_parts:
            logger.error(f"Bucket metric config missing 'promql_parts': {params.metric_config}")
            return [], None

        # Generate queries for each bucket
        for bucket in buckets:
            le_upper = bucket["le_upper"]
            le_lower = bucket["le_lower"]
            bucket_label = bucket.get("label", f"({le_lower},{le_upper}]")

            # Build upper and lower bucket queries with inner dimensions
            upper_template = promql_parts.get("upper_bucket", "")
            lower_template = promql_parts.get("lower_bucket", "")

            if not upper_template or not lower_template:
                logger.error(f"Bucket metric config missing promql_parts: {params.metric_config}")
                continue

            # Build inner queries with inner dimensions
            upper_inner = upper_template.format(
                group_by=inner_dims,
                filters=filters_str,
                time_window=params.time_window,
                le_upper=le_upper,
            )

            # For lower bucket, handle empty le_lower case (first bucket)
            if le_lower:
                lower_inner = lower_template.format(
                    group_by=inner_dims,
                    filters=filters_str,
                    time_window=params.time_window,
                    le_lower=le_lower,
                )
                # Build inner expression: upper - lower
                inner_promql = f"({upper_inner}) - ({lower_inner})"
            else:
                # First bucket: just use upper (no subtraction needed)
                inner_promql = upper_inner

            # Generate stats queries if needed
            if params.need_stats and stats_aggs:
                for stat_agg in stats_aggs:
                    # Wrap inner query with stats aggregation
                    outer_promql = f"{stat_agg.value} by ({outer_dims}) ({inner_promql})"

                    # Add label_replace to mark this as a bucket query with stat type
                    outer_promql = f'label_replace({outer_promql}, "bucket_label", "{bucket_label}", "", "")'
                    outer_promql = f'label_replace({outer_promql}, "query_type", "{stat_agg.value}", "", "")'

                    query_configs.append(
                        {
                            "data_source_label": "prometheus",
                            "data_type_label": "time_series",
                            "promql": outer_promql,
                            "interval": params.time_window,
                            "alias": f"{bucket_label}_{stat_agg.value}",
                        }
                    )

            # Bucket type needs to calculate stats from overall series
            outer_promql = f"{overall_agg.value} by ({outer_dims}) ({inner_promql})"
            outer_promql = f'label_replace({outer_promql}, "bucket_label", "{bucket_label}", "", "")'
            outer_promql = f'label_replace({outer_promql}, "query_type", "overall", "", "")'
            query_configs.append(
                {
                    "data_source_label": "prometheus",
                    "data_type_label": "time_series",
                    "promql": outer_promql,
                    "interval": params.time_window,
                    "alias": bucket_label,
                }
            )

        return query_configs, None

    def _build_capacity_queries(self, params: MetricsQueryParams) -> Tuple[List[dict], Optional[str]]:
        """
        Build queries for capacity metrics (used/total/available).

        Capacity metrics produce 3 sub-metric series, each labeled with a capacity_type
        dimension (used/total/available). Available is computed as total - used in PromQL.
        """
        inner_dims, outer_dims, filters_str, overall_agg, stats_aggs = self._prepare_query_context(params)

        sub_metrics = params.metric_config.get("sub_metrics", {})
        used_template = sub_metrics.get("used", "")
        total_template = sub_metrics.get("total", "")

        if not used_template or not total_template:
            logger.error(f"Capacity metric config missing sub_metrics: {params.metric_config}")
            return [], None

        used_base = used_template.format(filters=filters_str)
        total_base = total_template.format(filters=filters_str)

        used_inner = f"{overall_agg.value} by ({inner_dims}) ({used_base})"
        total_inner = f"{overall_agg.value} by ({inner_dims}) ({total_base})"
        avail_inner = f"clamp_min(({total_inner}) - ({used_inner}), 0)"

        sub_metric_queries = {
            "used": used_inner,
            "total": total_inner,
            "available": avail_inner,
        }

        query_configs = []

        for cap_type, inner_promql in sub_metric_queries.items():
            if params.need_stats and stats_aggs:
                for stat_agg in stats_aggs:
                    outer_promql = f"{stat_agg.value} by ({outer_dims}) ({inner_promql})"
                    outer_promql = f'label_replace({outer_promql}, "capacity_type", "{cap_type}", "", "")'
                    outer_promql = f'label_replace({outer_promql}, "query_type", "{stat_agg.value}", "", "")'
                    query_configs.append(
                        {
                            "data_source_label": "prometheus",
                            "data_type_label": "time_series",
                            "promql": outer_promql,
                            "interval": params.time_window,
                            "alias": f"{cap_type}_{stat_agg.value}",
                        }
                    )

            if params.need_overall:
                outer_promql = f"{overall_agg.value} by ({outer_dims}) ({inner_promql})"
                outer_promql = f'label_replace({outer_promql}, "capacity_type", "{cap_type}", "", "")'
                outer_promql = f'label_replace({outer_promql}, "query_type", "overall", "", "")'
                query_configs.append(
                    {
                        "data_source_label": "prometheus",
                        "data_type_label": "time_series",
                        "promql": outer_promql,
                        "interval": params.time_window,
                        "alias": cap_type,
                    }
                )

        return query_configs, None

    def _build_queries(self, params: MetricsQueryParams) -> Tuple[List[dict], Optional[str]]:
        """
        Build PromQL queries from metric config using two-level aggregation approach.

        Two-level structure:
        1. Inner query: Uses cluster_domain + required_dimensions (ensures base granularity)
        2. Outer aggregation: Wraps inner query with dimensions based on user's group_by choice

        Args:
            params: MetricsQueryParams object containing all query parameters

        Returns:
            Tuple of (List of query configs, None - expressions are integrated into PromQL)
        """
        # Step 1: Check for special metric types
        if params.metric_config.get("is_capacity"):
            return self._build_capacity_queries(params)

        buckets = params.metric_config.get("buckets")
        if buckets:
            return self._build_bucket_queries(params, buckets)

        # Step 2: Resolve dimensions for inner and outer queries
        inner_dims, outer_dims, filters_str, overall_agg, stats_aggs = self._prepare_query_context(params)

        query_configs = []

        # Step 4: Build inner query (base PromQL with inner dimensions)
        promql_parts = params.metric_config.get("promql_parts")
        is_composite = bool(promql_parts)

        if is_composite:
            # Composite metric: build a and b parts separately, then combine
            part_a_template = promql_parts.get("a", "")
            part_b_template = promql_parts.get("b", "")
            main_template = params.metric_config.get("promql_template", "{a} / {b}")

            if not part_a_template or not part_b_template:
                logger.error(f"Composite metric config missing a and b parts in promql_parts: {params.metric_config}")
                return [], None

            # Build part a and b base queries (no aggregation params for composite metrics)
            part_a_base = part_a_template.format(
                filters=filters_str,
                time_window=params.time_window,
            )

            part_b_base = part_b_template.format(
                filters=filters_str,
                time_window=params.time_window,
            )

            # Wrap base queries with inner aggregation explicitly
            part_a_promql = f"{overall_agg.value} by ({inner_dims}) ({part_a_base})"
            part_b_promql = f"{overall_agg.value} by ({inner_dims}) ({part_b_base})"

            # Build inner query expression
            inner_promql = main_template.format(
                a=part_a_promql,
                b=part_b_promql,
            )
        else:
            # Simple metric: single template with inner dimensions
            promql_template = params.metric_config.get("promql_template", "")
            if not promql_template:
                logger.error(f"Metric config missing 'promql_template': {params.metric_config}")
                return [], None

            inner_promql = promql_template.format(
                overall_agg=overall_agg.value,
                group_by=inner_dims,
                filters=filters_str,
                time_window=params.time_window,
            )

        # Step 5: Build outer aggregation queries (wrap inner query)
        # For stats mode: wrap inner query with stats aggregation functions
        if params.need_stats and stats_aggs:
            for stat_agg in stats_aggs:
                # Outer aggregation: stats_agg by (outer_dims) (inner_query)
                outer_promql = f"{stat_agg.value} by ({outer_dims}) ({inner_promql})"
                outer_promql = f'label_replace({outer_promql}, "query_type", "{stat_agg.value}", "", "")'

                query_configs.append(
                    {
                        "data_source_label": "prometheus",
                        "data_type_label": "time_series",
                        "promql": outer_promql,
                        "interval": params.time_window,
                        "alias": stat_agg.value,
                    }
                )

        # Step 6: Build queries for overall mode (if needed)
        if params.need_overall:
            # Outer aggregation: overall_agg by (outer_dims) (inner_query)
            outer_promql = f"{overall_agg.value} by ({outer_dims}) ({inner_promql})"
            outer_promql = f'label_replace({outer_promql}, "query_type", "overall", "", "")'
            query_configs.append(
                {
                    "data_source_label": "prometheus",
                    "data_type_label": "time_series",
                    "promql": outer_promql,
                    "interval": params.time_window,
                    "alias": "overall",
                }
            )

        return query_configs, None

    @staticmethod
    def _validate_time_range(time_range: Tuple[int, int]) -> Optional[dict]:
        """Return an error dict if time_range is unsafe for BKMonitor, else None."""
        if not time_range or len(time_range) != 2:
            return {"error": "invalid_time_range", "detail": "time_range must be (start, end) unix timestamps"}
        start_ts, end_ts = int(time_range[0]), int(time_range[1])
        if end_ts <= start_ts:
            return {"error": "invalid_time_range", "detail": "end must be greater than start"}
        now_ts = int(time.time())
        if end_ts > now_ts + METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS:
            return {
                "error": "invalid_time_range",
                "detail": f"end cannot be more than {METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS}s ahead of server time",
            }
        span = end_ts - start_ts
        if span > METRICS_MAX_QUERY_RANGE_SECONDS:
            return {
                "error": "invalid_time_range",
                "detail": f"range cannot exceed {METRICS_MAX_QUERY_RANGE_SECONDS} seconds",
            }
        return None

    def _build_query_params(
        self,
        query_configs: List[dict],
        time_range: Tuple[int, int],
        expression: Optional[str] = None,
    ) -> dict:
        """
        Prepare query parameters for BKMonitor unify_query API.

        Args:
            query_configs: List of query configurations
            time_range: Tuple of (start_time, end_time) in Unix timestamp
            expression: Optional expression to combine multiple queries (for composite metrics)

        Returns:
            Dict of parameters ready for unify_query API
        """
        params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        params["query_configs"] = query_configs
        params["start_time"] = time_range[0]
        params["end_time"] = time_range[1]

        # Add expression for composite metrics
        if expression:
            params["expression"] = expression

        return params

    def _determine_aggregation_level(
        self,
        ip_filters: Optional[List[str]] = None,
        instance_filters: Optional[List[InstanceFilter]] = None,
    ) -> AggregationLevel:
        """
        Determine the aggregation level based on provided filters.

        Args:
            ip_filters: Optional IP address filters
            instance_filters: Optional ip:port pair filters

        Returns:
            AggregationLevel enum value
        """
        has_ip = bool(ip_filters)
        has_instance = bool(instance_filters)
        if has_instance:
            return AggregationLevel.INSTANCE
        elif has_ip:
            return AggregationLevel.MACHINE

        return AggregationLevel.CLUSTER

    def _calculate_trend(
        self,
        data: Union[List[List[float]], List[float]],
        interval_sec: Optional[int] = None,
    ) -> float:
        """
        Calculate linear trend (slope) from time series data.

        Uses simple linear regression: y = mx + b, returns m (slope)
        Positive slope = increasing trend, negative = decreasing trend

        Args:
            data: Time series data [[value, timestamp], ...] or [value, ...] (values only)
            interval_sec: If provided, normalize slope to (metric unit)/minute by dividing
                by (interval_sec/60) i.e. slope * 60 / interval_sec

        Returns:
            Slope value (trend direction and magnitude).
            When interval_sec is provided, returns slope * 60 / interval_sec so unit is (metric)/min.
        """
        # Handle both List[List[float]] and List[float] for backward compatibility
        if not data or len(data) < 2:
            return 0.0

        # Check if input is List[List[float]] (time series) or List[float] (values only)
        if isinstance(data[0], list):
            # Extract values and create x indices
            points = [(i, point[0]) for i, point in enumerate(data) if point[0] is not None]
        else:
            # Already values only, create x indices
            points = [(i, val) for i, val in enumerate(data) if val is not None]

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

        def _round_sig2(v: float) -> float:
            if v == 0:
                return 0.0
            magnitude = math.floor(math.log10(abs(v)))
            factor = 10 ** (magnitude - 1)
            return round(v / factor) * factor

        if interval_sec and interval_sec > 0:
            return _round_sig2(slope * 60 / interval_sec)
        return _round_sig2(slope)

    def _calculate_median(self, data: Union[List[List[float]], List[float]]) -> float:
        """
        Calculate median value from time series data.

        Args:
            data: Time series data [[value, timestamp], ...] or [value, ...] (values only)

        Returns:
            Median value, or 0.0 if data is empty or has no valid values
        """
        # Handle both List[List[float]] and List[float] for backward compatibility
        if not data:
            return 0.0

        # Extract values if input is List[List[float]], otherwise use directly
        if isinstance(data[0], list):
            values = [point[0] for point in data if point[0] is not None]
        else:
            values = [val for val in data if val is not None]

        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        if n % 2 == 0:
            # Even number of values: average of two middle values
            median = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0
        else:
            # Odd number of values: middle value
            median = sorted_values[n // 2]

        return median

    def _calculate_p95(self, data: Union[List[List[float]], List[float]]) -> float:
        """
        Calculate 95th percentile from time series data.

        Args:
            data: Time series data [[value, timestamp], ...] or [value, ...] (values only)

        Returns:
            95th percentile value, or 0.0 if data is empty or has no valid values
        """
        # Handle both List[List[float]] and List[float] for backward compatibility
        if not data:
            return 0.0

        # Extract values if input is List[List[float]], otherwise use directly
        if isinstance(data[0], list):
            values = [point[0] for point in data if point[0] is not None]
        else:
            values = [val for val in data if val is not None]

        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        if n == 0:
            return 0.0

        # Calculate index for 95th percentile
        index = int(n * 0.95)
        # Clamp index to valid range
        index = min(index, n - 1)
        return sorted_values[index]

    def _calculate_stddev(self, data: Union[List[List[float]], List[float]]) -> float:
        """
        Calculate population standard deviation from time series data.

        Args:
            data: Time series data [[value, timestamp], ...] or [value, ...] (values only)

        Returns:
            Standard deviation, or 0.0 if data is empty or has no valid values
        """
        # Handle both List[List[float]] and List[float] for backward compatibility
        if not data:
            return 0.0

        # Extract values if input is List[List[float]], otherwise use directly
        if isinstance(data[0], list):
            values = [point[0] for point in data if point[0] is not None]
        else:
            values = [val for val in data if val is not None]

        if not values or len(values) < 2:
            return 0.0

        # Calculate mean
        mean = sum(values) / len(values)

        # Calculate variance: sum((x - mean)²) / n
        variance = sum((x - mean) ** 2 for x in values) / len(values)

        # Return standard deviation
        return variance**0.5

    @staticmethod
    def normalize_timestamps(datapoints: List[List[float]]) -> List[List[float]]:
        if not datapoints:
            return datapoints

        for point in datapoints:
            point[1] = point[1] / 1000

        return datapoints

    @staticmethod
    def _build_stats_key(dimensions: dict, cluster_domain: str, aggregation_level: AggregationLevel) -> str:
        """
        Build a key for storing statistics series based on dimensions.

        Iterates over all dimensions and builds key by joining them in priority order.
        Priority order: bucket_label > cmd > ip:port/ip > other dimensions > cluster_domain (fallback)

        Args:
            dimensions: Series dimensions dict containing ip, port, cmd, bucket_label, etc.
            cluster_domain: Cluster domain name

        Returns:
            Key string for organizing stats series (e.g., "ip:port", "cmd", "cmd@ip:port")
        """
        # Define dimension priority order and excluded dimensions
        dimension_priority = ["bucket_label", "cmd"]
        excluded = {"cluster_domain", "ip", "instance_port", "query_type"}

        key_parts = []

        # Process priority dimensions first
        for dim_name in dimension_priority:
            if dim_name in dimensions and dimensions[dim_name]:
                key_parts.append(dimensions[dim_name])

        # Handle ip:port combination (special case - combine ip and port)
        ip = dimensions.get("ip")
        port = dimensions.get("instance_port")
        instance = dimensions.get("instance")
        if instance and (not ip or not port) and ":" in instance:
            parsed_ip, parsed_port = instance.rsplit(":", 1)
            ip = ip or parsed_ip
            port = port or parsed_port
        if aggregation_level == AggregationLevel.CLUSTER:
            if ip and port:
                key_parts.append(f"{ip}:{port}")
            elif ip:
                key_parts.append(ip)
        elif aggregation_level == AggregationLevel.MACHINE and ip and port:
            key_parts.append(f"{ip}:{port}")

        # Process remaining dimensions (excluding already processed and excluded ones)
        for dim_name, dim_value in dimensions.items():
            if dim_name not in excluded and dim_name not in dimension_priority and dim_value:
                key_parts.append(dim_value)

        # Fallback to scope key if no other dimensions
        if not key_parts:
            if aggregation_level == AggregationLevel.MACHINE:
                return dimensions.get("ip") or cluster_domain
            if aggregation_level == AggregationLevel.INSTANCE:
                if dimensions.get("ip") and dimensions.get("instance_port"):
                    return f'{dimensions["ip"]}:{dimensions["instance_port"]}'
                return dimensions.get("ip") or cluster_domain
            return cluster_domain

        # Join parts with "@" separator
        return "@".join(key_parts)

    @staticmethod
    def _extract_scope_dimensions(dimensions: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract cluster/ip/port with fallback from instance label (ip:port)."""
        cluster_domain = dimensions.get("cluster_domain")
        ip = dimensions.get("ip")
        port = dimensions.get("instance_port")
        instance = dimensions.get("instance")

        if instance and (not ip or not port) and ":" in instance:
            parsed_ip, parsed_port = instance.rsplit(":", 1)
            ip = ip or parsed_ip
            port = port or parsed_port

        return cluster_domain, ip, port

    def _parse_response(
        self,
        response: dict,
        aggregation_level: AggregationLevel = AggregationLevel.CLUSTER,
    ) -> Dict[str, MetricSeries]:
        """
        Parse the unify_query response into MetricSeries per cluster.

        The API returns series with a "query_type" dimension (injected via label_replace).
        We use this to determine what type of statistic each series represents.
        Query types are parsed to AggFunction enum values and used as dictionary keys in stats_series_by_key.

        Args:
            response: Response from BKMonitor unify_query API
            aggregation_level: The level of aggregation being performed

        Returns:
            Dict mapping entity key to MetricSeries
            Note: stats_series_by_key uses AggFunction enum values as keys (e.g., AggFunction.MIN, AggFunction.MAX)
        """
        series_by_cluster = defaultdict(lambda: MetricSeries(aggregation_level=aggregation_level))
        series_list = response.get("series", [])

        for series in series_list:
            dimensions = series["dimensions"]
            # cluster_domain/ip/instance_port may be absent depending on metric label schema
            cluster_domain, ip, port = self._extract_scope_dimensions(dimensions)
            entity_key = cluster_domain or ip or (f"{ip}:{port}" if ip and port else "unknown")
            if aggregation_level == AggregationLevel.MACHINE:
                entity_key = ip or cluster_domain or "unknown"
            elif aggregation_level == AggregationLevel.INSTANCE:
                entity_key = f"{ip}:{port}" if ip and port else (ip or cluster_domain or "unknown")
            datapoints = series["datapoints"]

            self.normalize_timestamps(datapoints)

            # Get query_type from dimensions (injected via label_replace)
            query_type_str = dimensions.get("query_type")

            if not query_type_str:
                logger.warning(f"No query_type in dimensions: {dimensions}")
                continue

            # Parse query_type to enum (for stats aggregations) or keep as string (for "overall")
            query_type_enum = self._parse_query_type(query_type_str)

            # Handle statistical aggregations (min, max, avg, stddev)
            # Store datapoints only - scalar calculation will be done in _calculate_stats
            if query_type_enum is not None:
                # Skip if no valid datapoints
                if not datapoints or not any(point[0] is not None for point in datapoints):
                    continue

                # Initialize stats_series_by_key if needed
                if series_by_cluster[entity_key].stats_series_by_key is None:
                    series_by_cluster[entity_key].stats_series_by_key = {}

                # Build key for this stats series
                key_value = self._build_stats_key(dimensions, cluster_domain or "unknown", aggregation_level)

                # Initialize dict for this key if not exists
                if key_value not in series_by_cluster[entity_key].stats_series_by_key:
                    series_by_cluster[entity_key].stats_series_by_key[key_value] = {}

                # Store the datapoints for this query_type (use enum as key)
                series_by_cluster[entity_key].stats_series_by_key[key_value][query_type_enum] = datapoints

            elif query_type_str == "overall":
                # Build key based on aggregation level and available dimensions
                if not series_by_cluster[entity_key].raw_series:
                    series_by_cluster[entity_key].raw_series = {}

                # Check if this is a latency distribution bucket (has bucket_label)
                bucket_label = dimensions.get("bucket_label")
                if bucket_label:
                    _, ip, port = self._extract_scope_dimensions(dimensions)
                    port = dimensions.get("port") or port
                    cmd = dimensions.get("cmd")

                    parts = [bucket_label]
                    if cmd:
                        parts.append(cmd)
                    if aggregation_level == AggregationLevel.CLUSTER:
                        if ip and port:
                            parts.append(f"{ip}:{port}")
                        elif ip:
                            parts.append(ip)
                    elif aggregation_level == AggregationLevel.MACHINE and ip and port:
                        parts.append(f"{ip}:{port}")
                    key_value = "@".join(parts)
                else:
                    # Use the same key-building logic as stats series
                    key_value = self._build_stats_key(dimensions, cluster_domain or "unknown", aggregation_level)

                series_by_cluster[entity_key].raw_series[key_value] = datapoints
            else:
                logger.warning(f"Unknown query_type: {query_type_str}")

        return dict(series_by_cluster)

    def _compute_scalar_stats_from_values(
        self,
        values: List[float],
        interval_sec: Optional[int] = None,
        trend_unit: str = "",
    ) -> dict:
        """Compute min, max, avg, median, p95, cv, trend, latest from a list of values (no stddev in output)."""
        stats = {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "median": self._calculate_median(values),
            "p95": self._calculate_p95(values),
            "latest": values[-1],
            "trend": self._calculate_trend(values, interval_sec=interval_sec),
        }
        if trend_unit:
            stats["trend_unit"] = trend_unit
        stddev = self._calculate_stddev(values)
        stats["cv"] = (stddev / stats["avg"]) * 100 if stats["avg"] != 0 else 0.0
        return stats

    def _compute_stats_from_agg_series(
        self,
        stats_series_dict: dict,
        interval_sec: Optional[int] = None,
        trend_unit: str = "",
    ) -> dict:
        """
        Compute stats dict from stats_series_by_key entry (MIN/MAX/AVG/STDDEV series).
        Returns dict with min, max, avg, median, p95, trend, trend_unit, cv (stddev dropped).
        """
        stats = {}
        if AggFunction.MIN in stats_series_dict:
            min_values = [p[0] for p in stats_series_dict[AggFunction.MIN] if p[0] is not None]
            if min_values:
                stats["min"] = min(min_values)
        if AggFunction.MAX in stats_series_dict:
            max_values = [p[0] for p in stats_series_dict[AggFunction.MAX] if p[0] is not None]
            if max_values:
                stats["max"] = max(max_values)
                stats["latest"] = max_values[-1]
        if AggFunction.AVG in stats_series_dict:
            avg_values = [p[0] for p in stats_series_dict[AggFunction.AVG] if p[0] is not None]
            if avg_values:
                stats["avg"] = sum(avg_values) / len(avg_values)
                stats["median"] = self._calculate_median(avg_values)
                stats["p95"] = self._calculate_p95(avg_values)
                stats["trend"] = self._calculate_trend(avg_values, interval_sec=interval_sec)
                if trend_unit:
                    stats["trend_unit"] = trend_unit
        if AggFunction.STDDEV in stats_series_dict:
            stddev_values = [p[0] for p in stats_series_dict[AggFunction.STDDEV] if p[0] is not None]
            if stddev_values:
                stats["stddev"] = max(stddev_values)
        if "avg" in stats:
            stats["cv"] = (stats["stddev"] / stats["avg"]) * 100 if stats.get("stddev") and stats["avg"] != 0 else 0.0
        stats.pop("stddev", None)
        return stats

    def _calculate_stats(
        self,
        metric_series: MetricSeries,
        metric_config: dict,
        time_window: int = 60,
        metric_key: Optional[str] = None,
        vertical_stats: bool = False,
    ) -> None:
        """
        Calculate scalar statistics from parsed time series data.

        For bucket metrics or vertical_stats: Calculates stats from raw_series (temporal stats).
        For simple metrics (horizontal): Calculates stats from stats_series_by_key (cross-instance stats).

        Args:
            metric_series: MetricSeries object with parsed datapoints
                Note: stats_series_by_key uses AggFunction enum values as keys (e.g., AggFunction.MIN, AggFunction.MAX)
            metric_config: Metric configuration dict from METRIC_REGISTRY
            time_window: Time between consecutive data points (seconds), used to normalize trend to per-minute
            metric_key: Key from METRIC_REGISTRY, used to resolve trend_unit for output
            vertical_stats: When True, compute temporal stats from the aggregated raw_series
        """
        if metric_series.statistics is None:
            metric_series.statistics = {}

        trend_unit = TREND_UNIT_BY_METRIC_KEY.get(metric_key, "") if metric_key else ""

        if "buckets" in metric_config or vertical_stats:
            self._calculate_stats_from_raw_series(metric_series, interval_sec=time_window, trend_unit=trend_unit)
        else:
            self._calculate_stats_for_simple_metric(metric_series, interval_sec=time_window, trend_unit=trend_unit)

    def _calculate_stats_from_raw_series(
        self,
        metric_series: MetricSeries,
        interval_sec: Optional[int] = None,
        trend_unit: str = "",
    ) -> None:
        """Calculate stats from raw_series (used for bucket metrics and vertical stats)."""
        if not metric_series.raw_series:
            return
        for key_value, datapoints in metric_series.raw_series.items():
            values = [point[0] for point in datapoints if point[0] is not None]
            if not values:
                continue
            metric_series.statistics[key_value] = self._compute_scalar_stats_from_values(
                values, interval_sec=interval_sec, trend_unit=trend_unit
            )

    def _calculate_stats_for_simple_metric(
        self,
        metric_series: MetricSeries,
        interval_sec: Optional[int] = None,
        trend_unit: str = "",
    ) -> None:
        """Calculate stats from stats_series_by_key for simple metrics."""
        if not metric_series.stats_series_by_key:
            return
        for key_value, stats_series_dict in metric_series.stats_series_by_key.items():
            stats = self._compute_stats_from_agg_series(
                stats_series_dict, interval_sec=interval_sec, trend_unit=trend_unit
            )
            if stats:
                metric_series.statistics[key_value] = stats

    def _query_metrics_single_type(
        self,
        clusters: List[Cluster],
        metric_type: MetricType,
        time_range: Tuple[int, int],
        need_stats: bool,
        need_overall: bool,
        time_window: int = 60,
        instance_role: InstanceRole = InstanceRole.MASTER,
        ip_filters: Optional[List[str]] = None,
        instance_filters: Optional[List[InstanceFilter]] = None,
        group_by: Optional[List[MetricsGroupBy]] = None,
        vertical_stats: bool = False,
    ) -> Tuple[Optional[Dict[str, MetricSeries]], Optional[dict]]:
        if not clusters:
            logger.error("No clusters provided for metrics query")
            return None, {"error": "No clusters provided for metrics query"}
        cluster = clusters[0]

        # Auto-convert instance_role to PROXY for latency_distribution metric
        # This hides the restriction from users - they can pass any instance_role
        if metric_type == MetricType.LATENCY_DISTRIBUTION:
            instance_role = InstanceRole.PROXY

        aggregation_level = self._determine_aggregation_level(ip_filters, instance_filters)

        if group_by is None:
            group_by = []

        # Auto-inject CMD dimension for command_latency so users see per-command results by default
        if metric_type == MetricType.COMMAND_LATENCY:
            if MetricsGroupBy.CMD not in group_by:
                group_by = list(group_by) + [MetricsGroupBy.CMD]

        # Resolve metric key from registry
        metric_key = resolve_metric_key(cluster.cluster_type, metric_type, instance_role)
        if not metric_key:
            logger.error(
                f"No metric mapping found for cluster_type={cluster.cluster_type}, "
                f"metric_type={metric_type.value}, instance_role={instance_role.value}"
            )
            return None, {"error": "No metric mapping found", "metric_type": metric_type.value}

        metric_config = METRIC_REGISTRY.get(metric_key)
        if not metric_config:
            logger.error(f"No metric config found for metric_key={metric_key}")
            return None, {"error": "No metric config found", "metric_key": metric_key}

        # Build query parameters object
        query_params = MetricsQueryParams(
            cluster_domains=[current_cluster.immute_domain for current_cluster in clusters],
            metric_type=metric_type,
            metric_config=metric_config,
            aggregation_level=aggregation_level,
            time_window=time_window,
            instance_role=instance_role,
            ip_filters=ip_filters,
            instance_filters=instance_filters,
            need_stats=need_stats,
            need_overall=need_overall,
            group_by=group_by,
        )

        # Build all query configs
        expression = None
        if instance_filters:
            dedup_pairs = []
            pair_seen = set()
            for pair in instance_filters:
                key = (pair.ip, pair.port)
                if key in pair_seen:
                    continue
                pair_seen.add(key)
                dedup_pairs.append(pair)

            query_configs = []
            for pair in dedup_pairs:
                pair_query_params = MetricsQueryParams(
                    cluster_domains=query_params.cluster_domains,
                    metric_type=query_params.metric_type,
                    metric_config=query_params.metric_config,
                    aggregation_level=query_params.aggregation_level,
                    time_window=query_params.time_window,
                    instance_role=query_params.instance_role,
                    ip_filters=None,
                    instance_filters=[pair],
                    need_stats=query_params.need_stats,
                    need_overall=query_params.need_overall,
                    group_by=query_params.group_by,
                )
                pair_query_configs, _ = self._build_queries(pair_query_params)
                for query_config in pair_query_configs:
                    query_config["alias"] = f'{query_config["alias"]}_{pair.ip}:{pair.port}'
                query_configs.extend(pair_query_configs)
        else:
            query_configs, expression = self._build_queries(query_params)
        params = self._build_query_params(query_configs, time_range, expression)
        entity_count = max(len(clusters), len(ip_filters or []), len(instance_filters or []), 1)
        params["slimit"] = min(max(params.get("slimit", 500), entity_count * 200), 2000)

        logger.info(
            f"Querying {metric_type} metrics for clusters {[c.immute_domain for c in clusters]} "
            f"(role={instance_role}, ip_filters={ip_filters}, instance_filters={instance_filters}, group_by={group_by}) "
            f"with {len(query_configs)} query configs"
        )
        t0 = time.perf_counter()
        try:
            response = BKMonitorV3Api.unify_query(params)
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error(
                f"Failed to query metrics for clusters {[c.immute_domain for c in clusters]}: {e} "
                f"(unify_query duration_sec={elapsed:.3f})"
            )
            return None, {"error": str(e), "metric_key": metric_key, "retryable": True}
        elapsed = time.perf_counter() - t0
        logger.info(f"BKMonitor unify_query completed in {elapsed:.3f}s for metric_key={metric_key}")

        empty_series_error = {
            "error": "empty_series",
            "metric_key": metric_key,
            "aggregation_level": aggregation_level.value,
            "cluster_type": str(cluster.cluster_type),
            "filters": {
                "cluster_domains": query_params.cluster_domains,
                "instance_role": instance_role.value,
                "ip_filters": ip_filters or [],
                "instance_filters": [f"{pair.ip}:{pair.port}" for pair in (instance_filters or [])],
            },
            "promql": [qc.get("promql", "") for qc in query_configs],
        }

        if not response.get("series"):
            return None, empty_series_error

        series_by_cluster = self._parse_response(response, aggregation_level)
        if not series_by_cluster:
            return None, empty_series_error
        for series in series_by_cluster.values():
            self._calculate_stats(
                series, metric_config, time_window=time_window, metric_key=metric_key, vertical_stats=vertical_stats
            )

        return series_by_cluster, None

    def query_metrics(
        self,
        clusters: List[Cluster],
        metric_type: MetricType,
        time_range: Tuple[int, int],
        need_stats: bool,
        need_overall: bool,
        time_window: int = 60,
        instance_role: InstanceRole = InstanceRole.MASTER,
        ip_filters: Optional[List[str]] = None,
        instance_filters: Optional[List[InstanceFilter]] = None,
        group_by: Optional[List[MetricsGroupBy]] = None,
        vertical_stats: bool = False,
    ) -> Tuple[Dict[str, MetricSeries], List[dict]]:
        """
        Query metrics for one or more clusters, with optional filtering by machine/instance.

        Args:
            clusters: Cluster objects
            metric_type: Type of metric (MetricType enum)
            time_range: Tuple of (start_time, end_time) in Unix timestamp
            need_stats: Whether to include statistical queries (min/max/avg/stddev)
            need_overall: Whether to include overall time series queries
            time_window: Time window in seconds
            instance_role: Role of instances to query (InstanceRole enum)
            ip_filters: Optional IP filters
            instance_filters: Optional ip:port pair filters
            group_by: Optional list of dimensions for grouping results (e.g., [cluster_domain, ip], [instance]).
                Note: For COMMAND_LATENCY, CMD is always auto-injected regardless of group_by value.
            vertical_stats: When True, compute temporal stats from the aggregated raw_series

        Returns:
            Tuple of (merged MetricSeries dict, partial errors)
        """
        if not clusters:
            logger.error("No clusters provided for metrics query")
            return {}, [{"error": "No clusters provided for metrics query"}]

        time_err = self._validate_time_range(time_range)
        if time_err:
            return {}, [time_err]

        clusters_by_type: Dict[str, List[Cluster]] = defaultdict(list)
        for cluster in clusters:
            clusters_by_type[str(cluster.cluster_type)].append(cluster)

        merged_series: Dict[str, MetricSeries] = {}
        partial_errors: List[dict] = []

        for cluster_type, type_clusters in clusters_by_type.items():
            attempts = 0
            batch_result: Optional[Dict[str, MetricSeries]] = None
            batch_error: Optional[dict] = None
            while attempts < METRICS_QUERY_MAX_ATTEMPTS:
                attempts += 1
                batch_result, batch_error = self._query_metrics_single_type(
                    clusters=type_clusters,
                    metric_type=metric_type,
                    time_range=time_range,
                    need_stats=need_stats,
                    need_overall=need_overall,
                    time_window=time_window,
                    instance_role=instance_role,
                    ip_filters=ip_filters,
                    instance_filters=instance_filters,
                    group_by=group_by,
                    vertical_stats=vertical_stats,
                )
                if batch_result is not None:
                    break
                if not batch_error or not batch_error.get("retryable"):
                    break
                if attempts < METRICS_QUERY_MAX_ATTEMPTS:
                    time.sleep(METRICS_QUERY_RETRY_DELAY_SEC)

            if batch_result is None:
                partial_errors.append(
                    {
                        "cluster_type": cluster_type,
                        "attempt_count": attempts,
                        "error": f"Failed to query metrics for cluster_type={cluster_type}",
                        "detail": batch_error or {},
                    }
                )
                continue

            for key, series in batch_result.items():
                if key in merged_series:
                    partial_errors.append(
                        {
                            "cluster_type": cluster_type,
                            "attempt_count": attempts,
                            "error": f"Duplicate merged key detected: {key}",
                        }
                    )
                    continue
                merged_series[key] = series

        if not merged_series and partial_errors:
            partial_errors.append(
                {
                    "error": "No successful metric batches",
                    "metric_type": metric_type.value,
                    "aggregation_level": self._determine_aggregation_level(ip_filters, instance_filters).value,
                }
            )

        return merged_series, partial_errors
