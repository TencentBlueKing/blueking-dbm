# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.flow.plugins.components.collections.redis.redis_entry_check import RedisEntryCheckService


@pytest.fixture
def service():
    svc = RedisEntryCheckService()
    svc.log_warning = MagicMock()
    svc.log_exception = MagicMock()
    return svc


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
