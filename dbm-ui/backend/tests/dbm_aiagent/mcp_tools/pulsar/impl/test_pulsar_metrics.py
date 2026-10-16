# -*- coding: utf-8 -*-
"""Pulsar cluster ownership and monitor query space must stay separate."""
from unittest.mock import MagicMock, patch

import pytest

from backend.dbm_aiagent.mcp_tools.pulsar.impl import pulsar_metrics as mod

CLUSTER_BIZ_ID = 10001
MONITOR_BIZ_ID = 10002


@pytest.mark.parametrize("detail", [False, True])
@pytest.mark.parametrize("query_error", [False, True])
def test_monitor_space_preserves_cluster_business(monkeypatch, detail, query_error):
    monkeypatch.setattr(mod.env, "DBA_APP_BK_BIZ_ID", MONITOR_BIZ_ID)
    kwargs = {"bk_biz_id": CLUSTER_BIZ_ID, "cluster_domain": "test.cluster.db"}
    if detail:
        metric = next(iter(mod.PULSAR_DETAIL_METRICS_PROMQL))
        kwargs["metric_name"] = metric
        func = mod.query_pulsar_detail_metrics
        expected_promql = mod.PULSAR_DETAIL_METRICS_PROMQL[metric]["promql"].format(
            cluster_domain=kwargs["cluster_domain"], top_n=10
        )
    else:
        metric = next(iter(mod.PULSAR_METRICS_PROMQL))
        kwargs["metric_types"] = [metric]
        func = mod.query_pulsar_metrics
        expected_promql = mod.PULSAR_METRICS_PROMQL[metric]["promql"].replace("%s", kwargs["cluster_domain"])

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
        func = mod.query_pulsar_detail_metrics
        kwargs = {"metric_name": next(iter(mod.PULSAR_DETAIL_METRICS_PROMQL))}
    else:
        func = mod.query_pulsar_metrics
        kwargs = {"metric_types": [next(iter(mod.PULSAR_METRICS_PROMQL))]}

    with patch.object(mod.Cluster.objects, "get", side_effect=mod.Cluster.DoesNotExist), patch.object(
        mod.BKMonitorV3Api, "unify_query"
    ) as query:
        result = func(bk_biz_id=CLUSTER_BIZ_ID, cluster_domain="missing.db", **kwargs)

    assert result["error"] == "集群不存在: missing.db"
    query.assert_not_called()
