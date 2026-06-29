# -*- coding: utf-8 -*-
"""
Tests for capacity_disk outer aggregation respecting user group_by.
"""
import re

import pytest

from backend.dbm_aiagent.mcp_tools.redis.constants import METRIC_REGISTRY
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggregationLevel, MetricsGroupBy, MetricType
from backend.dbm_aiagent.mcp_tools.redis.models import MetricsQueryParams
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService


def _capacity_disk_params(group_by=None):
    return MetricsQueryParams(
        cluster_domains=["test.cluster"],
        metric_type=MetricType.CAPACITY,
        metric_config=METRIC_REGISTRY["capacity_disk"],
        aggregation_level=MetricsAggregationLevel.CLUSTER,
        group_by=group_by,
    )


def _extract_outer_by(promql: str) -> str:
    match = re.search(r"sum by \(([^)]+)\)", promql)
    assert match, f"no outer sum by clause in: {promql}"
    return match.group(1)


def _extract_inner_by(promql: str) -> str:
    match = re.search(r"max by \(([^)]+)\)", promql)
    assert match, f"no inner max by clause in: {promql}"
    return match.group(1)


@pytest.fixture
def svc():
    return RedisMetricsQueryService()


class TestCapacityDiskPromQL:
    @pytest.mark.parametrize(
        "group_by,expected_outer",
        [
            (None, "cluster_domain,mount_point"),
            ([MetricsGroupBy.CLUSTER_DOMAIN], "cluster_domain,mount_point"),
            ([MetricsGroupBy.IP], "cluster_domain,ip,mount_point"),
        ],
    )
    def test_outer_by_respects_group_by(self, svc, group_by, expected_outer):
        query_configs, _ = svc._build_capacity_queries(_capacity_disk_params(group_by=group_by))
        used_promql = next(cfg["promql"] for cfg in query_configs if cfg["alias"] == "used")
        assert _extract_inner_by(used_promql) == "cluster_domain,ip,mount_point"
        assert _extract_outer_by(used_promql) == expected_outer

    def test_instance_group_by_strips_instance_port_from_outer(self, svc):
        query_configs, _ = svc._build_capacity_queries(_capacity_disk_params(group_by=[MetricsGroupBy.INSTANCE]))
        used_promql = next(cfg["promql"] for cfg in query_configs if cfg["alias"] == "used")
        assert _extract_outer_by(used_promql) == "cluster_domain,ip,mount_point"
        assert "instance_port" not in _extract_outer_by(used_promql)


class TestCapacityDiskSeriesKeys:
    def test_cluster_scope_key_without_ip(self, svc):
        intrinsic_dims = svc._intrinsic_dimensions(METRIC_REGISTRY["capacity_disk"])
        key = svc._build_series_key(
            {"capacity_type": "used", "mount_point": "/data"},
            "test.cluster",
            MetricsAggregationLevel.CLUSTER,
            intrinsic_dims,
        )
        assert key == "used@/data"

    def test_ip_scope_key_includes_ip(self, svc):
        intrinsic_dims = svc._intrinsic_dimensions(METRIC_REGISTRY["capacity_disk"])
        key = svc._build_series_key(
            {"capacity_type": "used", "ip": "1.1.1.1", "mount_point": "/"},
            "test.cluster",
            MetricsAggregationLevel.CLUSTER,
            intrinsic_dims,
        )
        assert key == "used@1.1.1.1@/"

    def test_parse_cluster_aggregated_response(self, svc):
        response = {
            "series": [
                {
                    "dimensions": {
                        "cluster_domain": "test.cluster",
                        "mount_point": "/",
                        "capacity_type": "used",
                        "query_type": "overall",
                    },
                    "datapoints": [[100.0, 1_700_000_000]],
                }
            ]
        }
        parsed = svc._parse_response(
            response,
            METRIC_REGISTRY["capacity_disk"],
            MetricsAggregationLevel.CLUSTER,
        )
        assert list(parsed["test.cluster"].raw_series.keys()) == ["used@/"]

    def test_parse_ip_scoped_response(self, svc):
        response = {
            "series": [
                {
                    "dimensions": {
                        "cluster_domain": "test.cluster",
                        "ip": "1.1.1.1",
                        "mount_point": "/",
                        "capacity_type": "used",
                        "query_type": "overall",
                    },
                    "datapoints": [[100.0, 1_700_000_000]],
                },
                {
                    "dimensions": {
                        "cluster_domain": "test.cluster",
                        "ip": "2.2.2.2",
                        "mount_point": "/",
                        "capacity_type": "used",
                        "query_type": "overall",
                    },
                    "datapoints": [[80.0, 1_700_000_000]],
                },
            ]
        }
        parsed = svc._parse_response(
            response,
            METRIC_REGISTRY["capacity_disk"],
            MetricsAggregationLevel.CLUSTER,
        )
        keys = list(parsed["test.cluster"].raw_series.keys())
        assert sorted(keys) == ["used@1.1.1.1@/", "used@2.2.2.2@/"]
