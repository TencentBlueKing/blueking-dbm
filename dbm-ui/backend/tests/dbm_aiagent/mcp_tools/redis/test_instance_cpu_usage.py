# -*- coding: utf-8 -*-
"""Tests for redis/proxy instance_cpu_usage PromQL construction and API choices."""
import pytest

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.redis.constants import METRIC_REGISTRY, TREND_UNIT_BY_METRIC_KEY
from backend.dbm_aiagent.mcp_tools.redis.enums import (
    MetricsAggregationLevel,
    MetricsGroupBy,
    MetricsInstanceRole,
    MetricType,
)
from backend.dbm_aiagent.mcp_tools.redis.models import MetricsQueryParams
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService
from backend.dbm_aiagent.mcp_tools.redis.utils import explain_missing_metric_key, resolve_metric_key


def _params(
    metric_key="redis_instance_cpu_usage",
    group_by=None,
    aggregation_level=MetricsAggregationLevel.CLUSTER,
    instance_role=MetricsInstanceRole.MASTER,
    instance_filters=None,
):
    return MetricsQueryParams(
        cluster_domains=["test.cluster"],
        metric_type=MetricType.INSTANCE_CPU_USAGE,
        metric_config=METRIC_REGISTRY[metric_key],
        aggregation_level=aggregation_level,
        group_by=group_by,
        instance_role=instance_role,
        instance_filters=instance_filters,
        time_window=60,
    )


@pytest.fixture
def svc():
    return RedisMetricsQueryService()


class TestInstanceCpuUsageRegistry:
    def test_registry_and_trend_unit_present(self):
        for key in ("redis_instance_cpu_usage", "twemproxy_instance_cpu_usage"):
            assert key in METRIC_REGISTRY
            assert TREND_UNIT_BY_METRIC_KEY[key] == "%/min"
        assert "predixy_instance_cpu_usage" not in METRIC_REGISTRY
        assert "predixy_instance_cpu_usage" not in TREND_UNIT_BY_METRIC_KEY

    @pytest.mark.parametrize(
        "cluster_type,role,expected",
        [
            (ClusterType.TendisTwemproxyRedisInstance.value, MetricsInstanceRole.MASTER, "redis_instance_cpu_usage"),
            (
                ClusterType.TendisTwemproxyRedisInstance.value,
                MetricsInstanceRole.PROXY,
                "twemproxy_instance_cpu_usage",
            ),
            (ClusterType.TendisPredixyRedisCluster.value, MetricsInstanceRole.MASTER, "redis_instance_cpu_usage"),
        ],
    )
    def test_resolve_metric_key(self, cluster_type, role, expected):
        assert resolve_metric_key(cluster_type, MetricType.INSTANCE_CPU_USAGE, role) == expected

    def test_predixy_proxy_has_no_instance_cpu_mapping(self):
        assert (
            resolve_metric_key(
                ClusterType.TendisPredixyRedisCluster.value,
                MetricType.INSTANCE_CPU_USAGE,
                MetricsInstanceRole.PROXY,
            )
            is None
        )
        msg = explain_missing_metric_key(
            ClusterType.TendisPredixyRedisCluster.value,
            MetricType.INSTANCE_CPU_USAGE,
            MetricsInstanceRole.PROXY,
        )
        assert "Predixy" in msg
        assert "cpu_usage" in msg

    def test_api_choices(self):
        proxy_values = {c[0] for c in MetricType.get_proxy_cluster_api_choices()}
        backend_values = {c[0] for c in MetricType.get_backend_cluster_api_choices()}
        instance_values = {c[0] for c in MetricType.get_instance_api_choices()}
        assert MetricType.INSTANCE_CPU_USAGE.value in proxy_values
        assert MetricType.INSTANCE_CPU_USAGE.value in backend_values
        assert MetricType.INSTANCE_CPU_USAGE.value in instance_values
        assert MetricType.CPU_USAGE.value not in instance_values


class TestRedisInstanceCpuUsagePromQL:
    def test_uses_exporter_user_and_sys_cpu(self, svc):
        query_configs, _ = svc._build_queries(_params(group_by=[MetricsGroupBy.CLUSTER_DOMAIN]))
        promql = query_configs[0]["promql"]
        assert "redis_cpu_user_seconds_total" in promql
        assert "redis_cpu_sys_seconds_total" in promql
        assert "cpu_summary:usage" not in promql
        assert "* 100" in promql

    def test_inner_requires_instance_dims_outer_max_at_cluster(self, svc):
        query_configs, _ = svc._build_queries(_params(group_by=[MetricsGroupBy.CLUSTER_DOMAIN]))
        promql = query_configs[0]["promql"]
        assert "max by (cluster_domain,ip,instance_port)" in promql
        assert promql.startswith("label_replace(max by (cluster_domain)")

    def test_machine_level_max_among_instances(self, svc):
        query_configs, _ = svc._build_queries(
            _params(group_by=[MetricsGroupBy.IP], aggregation_level=MetricsAggregationLevel.MACHINE)
        )
        promql = query_configs[0]["promql"]
        assert "max by (ip,instance_port)" in promql
        assert "max by (cluster_domain,ip)" in promql


class TestProxyInstanceCpuUsagePromQL:
    def test_twemproxy_uses_process_cpu(self, svc):
        query_configs, _ = svc._build_queries(
            _params(
                metric_key="twemproxy_instance_cpu_usage",
                group_by=[MetricsGroupBy.CLUSTER_DOMAIN],
                instance_role=MetricsInstanceRole.PROXY,
            )
        )
        promql = query_configs[0]["promql"]
        assert "twemproxy_process_cpu" in promql
        assert "/ 100" in promql
        assert "max by (cluster_domain,ip,instance_port)" in promql
        assert promql.startswith("label_replace(max by (cluster_domain)")
