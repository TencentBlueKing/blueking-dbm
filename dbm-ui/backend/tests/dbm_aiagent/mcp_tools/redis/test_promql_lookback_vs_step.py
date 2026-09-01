# -*- coding: utf-8 -*-
"""PromQL lookback stays fixed; only unify_query interval follows max_len_datapoints."""
from datetime import datetime, timedelta

import pytest

from backend.dbm_aiagent.mcp_tools.redis.constants import METRIC_REGISTRY, METRICS_PROMQL_LOOKBACK_SECONDS
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggregationLevel, MetricType
from backend.dbm_aiagent.mcp_tools.redis.models import MetricsQueryParams
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService
from backend.dbm_aiagent.mcp_tools.redis.utils import calculate_time_range_window


class TestCalculateTimeRangeWindowStep:
    def test_long_range_raises_step_not_lookback_constant(self):
        end = datetime(2026, 7, 23, 12, 0, 0)
        start = end - timedelta(days=30)
        _, step = calculate_time_range_window(100, start, end)
        # 30d / 100 ≈ 25920s (432m)
        assert step == 30 * 24 * 60 * 60 // 100
        assert step > METRICS_PROMQL_LOOKBACK_SECONDS
        assert METRICS_PROMQL_LOOKBACK_SECONDS == 60


class TestPromqlLookbackFixed:
    @pytest.fixture
    def svc(self):
        return RedisMetricsQueryService()

    def test_cpu_promql_uses_fixed_lookback_while_interval_uses_step(self, svc):
        step = 25920  # 432m, as for 30d/100 points
        params = MetricsQueryParams(
            cluster_domains=["ssd295.amsuserlimitfork6.iegams.db"],
            metric_type=MetricType.CPU_USAGE,
            metric_config=METRIC_REGISTRY["twemproxy_cpu_usage"],
            aggregation_level=MetricsAggregationLevel.MACHINE,
            time_window=step,
            ip_filters=["1.1.1.1"],
        )
        query_configs, _ = svc._build_queries(params)
        assert len(query_configs) == 1
        promql = query_configs[0]["promql"]
        assert f"[{METRICS_PROMQL_LOOKBACK_SECONDS}s]" in promql
        assert f"[{step}s]" not in promql
        assert query_configs[0]["interval"] == step
