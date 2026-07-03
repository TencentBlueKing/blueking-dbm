# -*- coding: utf-8 -*-
from unittest.mock import patch

import pytest

from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.models import MetaCheckReport
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter, _chunked, safe_write_meta_reports

pytestmark = pytest.mark.django_db


class _FakeCluster:
    def __init__(self, cluster_id: int, domain: str):
        self.id = cluster_id
        self.immute_domain = domain
        self.cluster_type = "TendisPredixyRedisCluster"
        self.bk_biz_id = 1001
        self.bk_cloud_id = 0


def _meta_row(cluster: _FakeCluster, ip: str, state: str, msg: str = "test") -> dict:
    return {
        "cluster": cluster,
        "ip": ip,
        "port": 30000,
        "subtype": MetaCheckSubType.EntryInconsistent,
        "msg": msg,
        "state": state,
        "creator": "pytest",
    }


def test_chunked_splits_list():
    assert list(_chunked(list(range(5)), 2)) == [[0, 1], [2, 3], [4]]


def test_bulk_add_mode_preserves_failed_days_per_ip():
    cluster = _FakeCluster(90001, "redis-meta-bulk-a.db")
    MetaCheckReport.objects.filter(cluster=cluster.immute_domain).delete()

    writer = RedisReportWriter()
    rows = [
        _meta_row(cluster, "1.1.1.1", ReportStateType.ABNORMAL.value),
        _meta_row(cluster, "1.1.1.2", ReportStateType.ABNORMAL.value),
    ]
    writer.write_meta_reports(rows)

    failed_days = {
        row.ip: row.failed_days for row in MetaCheckReport.objects.filter(cluster=cluster.immute_domain).order_by("ip")
    }
    assert failed_days == {"1.1.1.1": 1, "1.1.1.2": 1}


def test_bulk_add_mode_increments_duplicate_key_in_same_batch():
    cluster = _FakeCluster(90002, "redis-meta-bulk-b.db")
    MetaCheckReport.objects.filter(cluster=cluster.immute_domain).delete()

    writer = RedisReportWriter()
    writer.write_meta_reports(
        [
            _meta_row(cluster, "1.1.1.1", ReportStateType.ABNORMAL.value, msg="first"),
            _meta_row(cluster, "1.1.1.1", ReportStateType.ABNORMAL.value, msg="second"),
        ]
    )

    assert list(
        MetaCheckReport.objects.filter(cluster=cluster.immute_domain)
        .order_by("create_at")
        .values_list("failed_days", flat=True)
    ) == [1, 2]


def test_bulk_add_mode_chunks_large_batches(monkeypatch):
    cluster = _FakeCluster(90003, "redis-meta-bulk-c.db")
    MetaCheckReport.objects.filter(cluster=cluster.immute_domain).delete()

    bulk_create_calls = []
    original_bulk_create = MetaCheckReport.objects.bulk_create

    def _track_bulk_create(objs, *args, **kwargs):
        bulk_create_calls.append(len(objs))
        return original_bulk_create(objs, *args, **kwargs)

    monkeypatch.setattr(MetaCheckReport.objects, "bulk_create", _track_bulk_create)
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_report_utils.META_REPORT_WRITE_CHUNK",
        2,
    )

    writer = RedisReportWriter()
    rows = [_meta_row(cluster, f"1.1.1.{idx}", ReportStateType.ABNORMAL.value) for idx in range(5)]
    writer.write_meta_reports(rows)

    assert bulk_create_calls == [2, 2, 1]
    assert MetaCheckReport.objects.filter(cluster=cluster.immute_domain).count() == 5


def test_safe_write_meta_reports_returns_false_on_db_error():
    writer = RedisReportWriter()
    with patch.object(writer, "write_meta_reports", side_effect=RuntimeError("db down")):
        assert safe_write_meta_reports(writer, [{"cluster": object()}], context="test") is False
