# -*- coding: utf-8 -*-
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.exceptions import ApiRequestError
from backend.flow.plugins.components.collections.redis.redis_entry_check import (
    CLB_DESCRIBE_HEALTH_QPS,
    RedisEntryCheckService,
)
from backend.flow.utils.clb_manage import CLBManage


@pytest.fixture
def service():
    svc = RedisEntryCheckService()
    svc.log_warning = MagicMock()
    svc.log_exception = MagicMock()
    return svc


@pytest.fixture
def health_gate():
    gate = MagicMock()
    with patch.object(RedisEntryCheckService, "clb_health_gate", gate):
        yield gate


def _proxy_cluster(entries, proxy_ips=("1.1.1.1",)):
    proxies = [SimpleNamespace(machine=SimpleNamespace(ip=ip)) for ip in proxy_ips]
    return SimpleNamespace(
        id=1,
        immute_domain="redis.test.db",
        bk_biz_id=1,
        bk_cloud_id=0,
        cluster_type=ClusterType.TendisPredixyRedisCluster.value,
        proxyinstance_set=SimpleNamespace(all=lambda: proxies),
        storageinstance_set=SimpleNamespace(all=lambda: []),
        clusterentry_set=SimpleNamespace(all=lambda: entries),
    )


def _clb_entry(clb_id="lb-1", clb_region="ap-guangzhou"):
    detail = SimpleNamespace(clb_id=clb_id, clb_ip="3.3.3.3", listener_id="lbl-1", clb_region=clb_region)
    return SimpleNamespace(
        entry="3.3.3.3",
        cluster_entry_type=ClusterEntryType.CLB.value,
        forward_to=None,
        clbentrydetail_set=SimpleNamespace(all=lambda: [detail]),
    )


def _entry(entry_type, name="redis.test.db"):
    return SimpleNamespace(entry=name, cluster_entry_type=entry_type, forward_to=None, detail={"polaris_name": "p"})


def test_clb_health_gate_spaces_calls_across_instances():
    first, second = RedisEntryCheckService(), RedisEntryCheckService()
    assert first.clb_health_gate is second.clb_health_gate

    first.clb_health_gate.acquire()
    start = time.monotonic()
    second.clb_health_gate.acquire()
    assert time.monotonic() - start >= 1.0 / CLB_DESCRIBE_HEALTH_QPS - 0.005


def test_health_query_only_for_clb_with_id_and_region(service, health_gate):
    cluster = _proxy_cluster([])
    with patch.object(CLBManage, "get_clb_rs", return_value=["1.1.1.1:30000"]), patch.object(
        CLBManage, "describe_target_health", return_value={"abnormalips": []}
    ) as describe, patch.object(service, "_get_dns_ips", return_value=({"1.1.1.1"}, None)), patch.object(
        service, "_get_polaris_ips", return_value=({"1.1.1.1"}, None)
    ):
        assert service._check_entry_consistency(cluster, _clb_entry()) is None
        assert describe.call_count == 1

        for entry in (
            _entry(ClusterEntryType.DNS.value),
            _entry(ClusterEntryType.CLBDNS.value),
            _entry(ClusterEntryType.POLARIS.value),
            _clb_entry(clb_id=""),
            _clb_entry(clb_region=""),
        ):
            service._check_entry_consistency(cluster, entry)

    assert describe.call_count == 1
    assert health_gate.acquire.call_count == 1


def test_unhealthy_is_listener_intersection(service, health_gate):
    cluster = _proxy_cluster([])
    with patch.object(CLBManage, "get_clb_rs", return_value=["1.1.1.1:30000"]), patch.object(
        CLBManage,
        "describe_target_health",
        return_value={"totalcount": 2, "abnormalcount": 2, "abnormalips": ["1.1.1.1:30000", "2.2.2.2:30000"]},
    ):
        detail = service._check_entry_consistency(cluster, _clb_entry())

    assert detail["unhealthy_rs"] == ["1.1.1.1:30000"]
    assert "missing_ips" not in detail
    row = RedisEntryCheckService._build_entry_report_row(cluster, [detail])
    assert row["state"] == ReportStateType.ABNORMAL
    assert row["subtype"] == MetaCheckSubType.EntryInconsistent
    assert "unhealthy: 1.1.1.1:30000" in row["msg"]
    assert "2.2.2.2" not in row["msg"]


def test_abnormal_outside_listener_keeps_report_normal(service, health_gate):
    cluster = _proxy_cluster([_clb_entry()])
    with patch.object(CLBManage, "get_clb_rs", return_value=["1.1.1.1:30000"]), patch.object(
        CLBManage, "describe_target_health", return_value={"abnormalcount": 1, "abnormalips": ["2.2.2.2:30000"]}
    ):
        result = service._check_single_cluster(cluster)

    assert result["inconsistent"] == 0
    assert result["report_row"]["state"] == ReportStateType.NORMAL


@pytest.mark.parametrize(
    "describe_kwargs",
    [
        {"side_effect": ApiRequestError("404 not found")},
        {"side_effect": RuntimeError("boom")},
        {"return_value": {}},
    ],
)
def test_health_query_failure_is_recorded_and_batch_continues(service, health_gate, describe_kwargs):
    dns_entry = _entry(ClusterEntryType.DNS.value)
    cluster = _proxy_cluster([_clb_entry(), dns_entry])
    with patch.object(CLBManage, "get_clb_rs", return_value=["1.1.1.1:30000"]), patch.object(
        CLBManage, "describe_target_health", **describe_kwargs
    ), patch.object(service, "_get_dns_ips", return_value=({"2.2.2.2"}, None)) as dns:
        result = service._check_single_cluster(cluster)

    assert "error" not in result
    assert result["checked"] == 2
    assert result["inconsistent"] == 2
    dns.assert_called_once()
    msg = result["report_row"]["msg"]
    assert "CLB target health query failed" in msg
    assert "unhealthy" not in msg


def test_membership_mismatch_and_health_failure_share_one_row(service, health_gate):
    cluster = _proxy_cluster([_clb_entry()], proxy_ips=("1.1.1.1", "1.1.1.9"))
    with patch.object(CLBManage, "get_clb_rs", return_value=["1.1.1.1:30000"]), patch.object(
        CLBManage, "describe_target_health", return_value={}
    ):
        result = service._check_single_cluster(cluster)

    row = result["report_row"]
    assert row["state"] == ReportStateType.ABNORMAL
    assert row["subtype"] == MetaCheckSubType.EntryInconsistent
    assert "missing: 1.1.1.9" in row["msg"]
    assert "CLB target health query failed" in row["msg"]


def test_load_batch_clusters_prefetches_clb_details():
    qs = MagicMock()
    qs.prefetch_related.return_value = []
    with patch(
        "backend.flow.plugins.components.collections.redis.redis_entry_check.Cluster.objects.filter",
        return_value=qs,
    ):
        RedisEntryCheckService._load_batch_clusters([1])

    assert "clusterentry_set__clbentrydetail_set" in qs.prefetch_related.call_args.args


def test_load_batch_clusters_prefetches_ids(service):
    cluster = SimpleNamespace(id=1)
    qs = MagicMock()
    qs.prefetch_related.return_value = [cluster]
    with patch(
        "backend.flow.plugins.components.collections.redis.redis_entry_check.Cluster.objects.filter",
        return_value=qs,
    ) as cluster_filter:
        result = RedisEntryCheckService._load_batch_clusters([1, 2])

    cluster_filter.assert_called_once_with(id__in=[1, 2])
    qs.prefetch_related.assert_called_once()
    assert result == {1: cluster}


def test_build_entry_report_row_normal(service):
    cluster = SimpleNamespace(id=1, immute_domain="redis.test.db")
    row = RedisEntryCheckService._build_entry_report_row(cluster, [])
    assert row["state"] == ReportStateType.NORMAL
    assert row["subtype"] == MetaCheckSubType.EntryInconsistent


def test_check_single_cluster_returns_report_row_without_db_write(service):
    cluster = SimpleNamespace(
        id=1,
        immute_domain="redis.test.db",
        cluster_type="TendisPredixyRedisCluster",
        clusterentry_set=SimpleNamespace(all=lambda: []),
    )
    with patch.object(service, "_check_entry_consistency", return_value=None):
        result = service._check_single_cluster(cluster)

    assert result["report_row"]["state"] == ReportStateType.NORMAL
    assert result["checked"] == 0


def test_schedule_writes_reports_on_main_thread(service):
    data = MagicMock()
    data.outputs = {
        "candidates_key": "key",
        "batch_size": 2,
        "current_batch": 0,
        "total_checked": 0,
        "total_inconsistent": 0,
        "total_batches": 1,
    }
    cluster = SimpleNamespace(id=1, immute_domain="redis.test.db")
    service._pop_batch_from_redis = MagicMock(return_value=[1])
    service._load_batch_clusters = MagicMock(return_value={1: cluster})
    service._check_single_cluster = MagicMock(
        return_value={
            "checked": 1,
            "inconsistent": 0,
            "report_row": {
                "cluster": cluster,
                "ip": None,
                "port": None,
                "subtype": MetaCheckSubType.EntryInconsistent,
                "msg": "ok",
                "state": ReportStateType.NORMAL,
                "creator": "system",
            },
        }
    )
    service.finish_schedule = MagicMock()
    service.log_info = MagicMock()

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_entry_check.safe_write_meta_reports",
        return_value=True,
    ) as safe_write:
        service._schedule(data, parent_data=None)

    safe_write.assert_called_once()
    service._check_single_cluster.assert_called_once_with(cluster)


def test_schedule_requeues_batch_when_write_fails(service):
    data = MagicMock()
    data.outputs = {
        "candidates_key": "key",
        "batch_size": 2,
        "current_batch": 0,
        "total_checked": 0,
        "total_inconsistent": 0,
        "total_batches": 2,
    }
    cluster = SimpleNamespace(id=1, immute_domain="redis.test.db")
    service._pop_batch_from_redis = MagicMock(return_value=[1, 2])
    service._load_batch_clusters = MagicMock(return_value={1: cluster})
    service._check_single_cluster = MagicMock(
        return_value={
            "checked": 1,
            "inconsistent": 0,
            "report_row": {
                "cluster": cluster,
                "ip": None,
                "port": None,
                "subtype": MetaCheckSubType.EntryInconsistent,
                "msg": "ok",
                "state": ReportStateType.NORMAL,
                "creator": "system",
            },
        }
    )
    service._requeue_batch_to_redis = MagicMock()
    service.log_warning = MagicMock()

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_entry_check.safe_write_meta_reports",
        return_value=False,
    ):
        service._schedule(data, parent_data=None)

    service._requeue_batch_to_redis.assert_called_once_with("key", [1, 2])
    assert data.outputs["current_batch"] == 0
