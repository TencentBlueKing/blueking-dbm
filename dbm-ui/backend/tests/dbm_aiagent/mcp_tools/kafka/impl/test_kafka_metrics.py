# -*- coding: utf-8 -*-
"""Kafka cluster ownership and monitor query space must stay separate."""
from unittest.mock import MagicMock, patch

import pytest

from backend.dbm_aiagent.mcp_tools.kafka.impl import kafka_metrics as mod
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_metrics import KafkaDetailMetricsOutputSerializer

CLUSTER_BIZ_ID = 10001
MONITOR_BIZ_ID = 10002


@pytest.mark.parametrize("detail", [False, True])
@pytest.mark.parametrize("query_error", [False, True])
def test_monitor_space_preserves_cluster_business(monkeypatch, detail, query_error):
    monkeypatch.setattr(mod.env, "DBA_APP_BK_BIZ_ID", MONITOR_BIZ_ID)
    kwargs = {"bk_biz_id": CLUSTER_BIZ_ID, "cluster_domain": "test.cluster.db"}
    if detail:
        metric = next(iter(mod.KAFKA_DETAIL_METRICS_PROMQL))
        kwargs["metric_name"] = metric
        func = mod.query_kafka_detail_metrics
        expected_promql = mod.KAFKA_DETAIL_METRICS_PROMQL[metric]["promql"].format(
            cluster_domain=kwargs["cluster_domain"], top_n=10
        )
    else:
        metric = next(iter(mod.KAFKA_METRICS_PROMQL))
        kwargs["metric_types"] = [metric]
        func = mod.query_kafka_metrics
        expected_promql = mod.KAFKA_METRICS_PROMQL[metric]["promql"].replace("%s", kwargs["cluster_domain"])

    with patch.object(mod, "Cluster") as cluster_cls, patch.object(mod.BKMonitorV3Api, "unify_query") as query:
        cluster_cls.objects.get.return_value = MagicMock(id=100)
        if query_error:
            query.side_effect = RuntimeError("monitor unavailable")
        else:
            query.return_value = {"series": [{"dimensions": {}, "datapoints": [[0, 1000], [2, 2000]]}]}
        result = func(**kwargs)

    cluster_cls.objects.get.assert_called_once_with(bk_biz_id=CLUSTER_BIZ_ID, immute_domain="test.cluster.db")
    query.assert_called_once()
    params = query.call_args.args[0]
    assert params["bk_biz_id"] == MONITOR_BIZ_ID
    assert params["query_configs"][0]["promql"] == expected_promql
    if not detail:
        assert result["bk_biz_id"] == CLUSTER_BIZ_ID
    if query_error:
        error = result["error"] if detail else result["metrics"][metric]["error"]
        assert error == "monitor unavailable"
    elif detail:
        assert result["total_series_count"] == 1
        assert result["items"][0]["latest_value"] == 2
    else:
        assert result["metrics"][metric]["statistics"]["count"] == 2


@pytest.mark.parametrize("detail", [False, True])
def test_missing_cluster_does_not_query_monitor(detail):
    if detail:
        func = mod.query_kafka_detail_metrics
        kwargs = {"metric_name": next(iter(mod.KAFKA_DETAIL_METRICS_PROMQL))}
    else:
        func = mod.query_kafka_metrics
        kwargs = {"metric_types": [next(iter(mod.KAFKA_METRICS_PROMQL))]}

    with patch.object(mod.Cluster.objects, "get", side_effect=mod.Cluster.DoesNotExist), patch.object(
        mod.BKMonitorV3Api, "unify_query"
    ) as query:
        result = func(bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="missing.db", **kwargs)

    assert result["error"] == "集群不存在: missing.db"
    query.assert_not_called()


@pytest.mark.parametrize(
    "dimensions, expected",
    [
        ({"bk_target_ip": "127.0.0.1", "ip": "127.0.0.2", "instance": "127.0.0.3-9092"}, "127.0.0.1"),
        ({"ip": "127.0.0.2"}, "127.0.0.2"),
        ({"instance": "127.0.0.3"}, "127.0.0.3"),
        ({"instance": "127.0.0.3-9092"}, "127.0.0.3"),
        ({"instance": "127.0.0.3:9092"}, "127.0.0.3"),
        ({"instance": "[2001:db8::1]:9092"}, "2001:db8::1"),
        ({"instance": "2001:db8::1"}, "2001:db8::1"),
        ({"bk_target_ip": "invalid", "instance": "127.0.0.3-9092"}, "127.0.0.3"),
        ({"instance": "broker.example.com:9092"}, None),
        ({"instance": None}, None),
        ({}, None),
    ],
)
def test_disk_host_ip(dimensions, expected):
    assert mod._disk_host_ip(dimensions) == expected


def _query_disk(series, top_n=10):
    with patch.object(mod.Cluster.objects, "get"), patch.object(
        mod.BKMonitorV3Api, "unify_query", return_value={"series": series}
    ):
        return mod.query_kafka_detail_metrics(
            bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="test.cluster.db", metric_name="disk_usage_detail", top_n=top_n
        )


def test_disk_details_preserve_host_identity_and_limit():
    series = [
        {
            "dimensions": {"bk_target_ip": "127.0.0.1", "instance": "127.0.0.1-9092", "mount_point": "/data"},
            "datapoints": [[80, 1000], [None, 2000], [85, 3000]],
        },
        {
            "dimensions": {"instance": "127.0.0.2-9092", "mount_point": "/data"},
            "datapoints": [[90, 1000], [95, 3000]],
        },
    ]
    result = _query_disk(series, top_n=1)

    assert result["total_series_count"] == 2
    assert result["metric_desc"] == "数据盘使用率按主机和挂载点(%)"
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item == {
        "label": "/data",
        "ip": "127.0.0.2",
        "instance": "127.0.0.2-9092",
        "mount_point": "/data",
        "dimensions": {"instance": "127.0.0.2-9092", "mount_point": "/data"},
        "latest_value": 95,
        "statistics": {"min": 90, "max": 95, "avg": 92.5, "latest": 95},
    }
    assert KafkaDetailMetricsOutputSerializer(result).data["items"][0] == item
    all_items = _query_disk(series)["items"]
    assert [row["ip"] for row in all_items] == ["127.0.0.2", "127.0.0.1"]
    assert all_items[1]["statistics"] == {"min": 80, "max": 85, "avg": 82.5, "latest": 85}


@pytest.mark.parametrize("datapoints", [[], [[None, 1000]]])
def test_disk_missing_dimensions_and_values(datapoints):
    item = _query_disk([{"datapoints": datapoints}])["items"][0]
    assert item["ip"] is None
    assert item["instance"] is None
    assert item["mount_point"] is None
    assert item["dimensions"] == {}
    assert item["label"] == "unknown"
    assert item["latest_value"] == 0
    assert item["statistics"] == {}


def test_disk_empty_response():
    result = _query_disk([])
    assert result["items"] == []
    assert result["total_series_count"] == 0


def test_disk_query_filters_system_disks():
    with patch.object(mod.Cluster.objects, "get"), patch.object(
        mod.BKMonitorV3Api, "unify_query", return_value={"series": []}
    ) as query:
        mod.query_kafka_detail_metrics(
            bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="test.cluster.db", metric_name="disk_usage_detail"
        )
    promql = query.call_args.args[0]["query_configs"][0]["promql"]
    assert 'cluster_domain="test.cluster.db"' in promql
    assert 'instance_role="broker"' in promql
    assert 'device_type=~"ext.?|xfs"' in promql
    assert 'mount_point!~"^(/|/usr/local)$"' in promql
    assert "max_over_time(" in promql
    assert "[5m]" in promql


def test_topic_detail_does_not_add_disk_fields():
    with patch.object(mod.Cluster.objects, "get"), patch.object(
        mod.BKMonitorV3Api,
        "unify_query",
        return_value={"series": [{"dimensions": {"topic": "orders"}, "datapoints": [[2, 1000]]}]},
    ):
        result = mod.query_kafka_detail_metrics(
            bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="test.cluster.db", metric_name="topic_traffic_in"
        )
    assert set(result["items"][0]) == {"label", "latest_value", "statistics"}


@pytest.mark.parametrize("metric_name", list(mod.KAFKA_DETAIL_METRICS_PROMQL))
def test_detail_top_n_limits_all_dimensions(metric_name):
    label_key = mod.KAFKA_DETAIL_METRICS_PROMQL[metric_name]["label_key"]
    series = [
        {"dimensions": {label_key: "first"}, "datapoints": [[10, 1000]]},
        {"dimensions": {label_key: "second"}, "datapoints": [[30, 1000]]},
        {"dimensions": {label_key: "third"}, "datapoints": [[20, 1000]]},
    ]
    with patch.object(mod.Cluster.objects, "get"), patch.object(
        mod.BKMonitorV3Api, "unify_query", return_value={"series": series}
    ):
        result = mod.query_kafka_detail_metrics(
            bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="test.cluster.db", metric_name=metric_name, top_n=2
        )
    assert result["total_series_count"] == 3
    assert [item["label"] for item in result["items"]] == ["second", "third"]
