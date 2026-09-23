# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import serializers as drf_serializers

from backend.db_services.redis.rollback.batches import BackupBatchService
from backend.db_services.redis.rollback.serializers import BackupBatchQuerySerializer
from backend.db_services.redis.rollback.shards import ShardRef


def _record(shard_value, file_name, source_ip="1.1.1.1", server_port=30000, hour="01", minute="00", size=1):
    return {
        "backup_identify": "SCHEDULED-2026010101",
        "shard_value": shard_value,
        "source_ip": source_ip,
        "server_port": server_port,
        "file_name": file_name,
        "task_id": "t-{}".format(file_name),
        "size": size,
        "backup_begin_time": "2026-01-01T{}:{}:00+00:00".format(hour, minute),
        "backup_end_time": "2026-01-01T{}:{}:30+00:00".format(hour, minute),
        "round_key": file_name,
    }


def _service(records, refs=None, by_identify=False):
    cluster = MagicMock()
    cluster.immute_domain = "cache.example.db"
    service = BackupBatchService(cluster)
    if by_identify:
        service.locator.locate_full_by_identify = MagicMock(return_value=records)
    else:
        service.locator.list_full_in_window = MagicMock(return_value=records)
    service.resolver.from_db_meta = MagicMock(return_value=refs or [])
    service.resolver.cluster_shard_map = MagicMock(return_value=[])
    return service


# --- list_batches: summary only ---------------------------------------------------------------


def test_list_batches_returns_summary_without_shard_tree():
    service = _service([_record("0-1", "a.aof.zst")])

    batch = service.list_batches()["batches"][0]

    assert "shards" not in batch
    assert "files" not in batch
    assert set(batch) == {
        "backup_identify",
        "backup_type",
        "start_time",
        "end_time",
        "total_size",
        "shard_count",
        "is_complete",
        "is_all_shards_covered",
        "has_multi_rounds",
        "source_is_all_current",
    }


def test_list_batches_filters_by_shard_value():
    service = _service(
        [
            _record("0-104999", "old.aof.zst", source_ip="3.3.3.3", size=10),
            _record("105000-209999", "cur.aof.zst", server_port=30001, size=11),
        ],
        refs=[
            ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True),
            ShardRef("105000-209999", current_master="1.1.1.1:30001", current_slave="1.1.1.9:30001", resolvable=True),
        ],
    )

    batch = service.list_batches(shard_values=["0-104999"])["batches"][0]

    assert batch["shard_count"] == 1
    assert batch["total_size"] == 10
    # Only one shard remains, failing to cover both current topology shards.
    assert batch["is_all_shards_covered"] is False
    # 3.3.3.3 is an old instance prior to host replacement.
    assert batch["source_is_all_current"] is False


def test_list_batches_summary_flags_when_batch_covers_topology():
    service = _service(
        [
            _record("0-104999", "a.aof.zst"),
            _record("105000-209999", "b.aof.zst", server_port=30001),
        ],
        refs=[
            ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True),
            ShardRef("105000-209999", current_master="1.1.1.1:30001", current_slave="1.1.1.9:30001", resolvable=True),
        ],
    )

    batch = service.list_batches()["batches"][0]

    assert batch["shard_count"] == 2
    assert batch["is_all_shards_covered"] is True
    assert batch["source_is_all_current"] is True
    assert batch["has_multi_rounds"] is False
    assert batch["is_complete"] is True
    assert batch["backup_type"] == "SCHEDULED"


def test_list_batches_flags_multi_rounds():
    service = _service(
        [
            _record("0-1", "r1.aof.zst", minute="00"),
            _record("0-1", "r2.aof.zst", minute="20"),
        ]
    )

    batch = service.list_batches()["batches"][0]

    assert batch["has_multi_rounds"] is True
    assert batch["shard_count"] == 1
    assert batch["total_size"] == 2


# --- batch_details: shard / round tree --------------------------------------------------------


def test_batch_details_filters_by_shard_value():
    service = _service(
        [
            _record("0-104999", "old.aof.zst", source_ip="3.3.3.3", size=10),
            _record("105000-209999", "cur.aof.zst", server_port=30001, size=11),
        ],
        refs=[
            ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True),
            ShardRef("105000-209999", current_master="1.1.1.1:30001", current_slave="1.1.1.9:30001", resolvable=True),
        ],
        by_identify=True,
    )

    result = service.batch_details("SCHEDULED-2026010101", shard_values=["0-104999"])

    assert result["backup_identify"] == "SCHEDULED-2026010101"
    assert [s["shard_value"] for s in result["shards"]] == ["0-104999"]
    round_detail = result["shards"][0]["rounds"][0]
    assert round_detail["source_ip"] == "3.3.3.3"
    assert round_detail["source_is_current"] is False
    assert result["shards"][0]["in_current_topology"] is True


def test_batch_details_groups_rounds_per_shard():
    service = _service(
        [
            _record("0-1", "r1.aof.zst", minute="00"),
            _record("0-1", "r2.aof.zst", minute="20"),
        ],
        by_identify=True,
    )

    rounds = service.batch_details("SCHEDULED-2026010101")["shards"][0]["rounds"]

    assert [r["round_key"] for r in rounds] == ["r2.aof.zst", "r1.aof.zst"]
    assert rounds[0]["is_latest"] is True
    assert rounds[1]["is_latest"] is False


def test_batch_details_marks_shard_absent_from_topology():
    service = _service([_record("0-104999", "a.aof.zst")], by_identify=True)

    shard = service.batch_details("SCHEDULED-2026010101")["shards"][0]

    assert shard["in_current_topology"] is False
    assert shard["current_master"] is None


def test_batch_details_round_keeps_all_split_files():
    service = _service(
        [
            dict(_record("0-1", "full.aof.zst.split.000", size=5), round_key="full.aof.zst"),
            dict(_record("0-1", "full.aof.zst.split.001", size=7), round_key="full.aof.zst"),
        ],
        by_identify=True,
    )

    rounds = service.batch_details("SCHEDULED-2026010101")["shards"][0]["rounds"]

    assert len(rounds) == 1
    assert rounds[0]["is_complete"] is True
    assert rounds[0]["size"] == 12
    assert len(rounds[0]["files"]) == 2


# --- query window guard -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "start_time,end_time",
    [
        ("2026-01-01T00:00:00+00:00", "2026-01-08T00:00:00+00:00"),
        ("2026-01-01T00:00:00+00:00", "2026-01-31T00:00:00+00:00"),
    ],
)
def test_batch_query_accepts_window_within_limit(start_time, end_time):
    serializer = BackupBatchQuerySerializer(data={"cluster_id": 1, "start_time": start_time, "end_time": end_time})
    assert serializer.is_valid(), serializer.errors


def test_batch_query_rejects_window_over_30_days():
    serializer = BackupBatchQuerySerializer(
        data={"cluster_id": 1, "start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-02-05T00:00:00+00:00"}
    )
    with pytest.raises(drf_serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_batch_query_rejects_reversed_window():
    serializer = BackupBatchQuerySerializer(
        data={"cluster_id": 1, "start_time": "2026-02-05T00:00:00+00:00", "end_time": "2026-01-01T00:00:00+00:00"}
    )
    with pytest.raises(drf_serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_batch_query_rejects_half_open_window():
    serializer = BackupBatchQuerySerializer(data={"cluster_id": 1, "start_time": "2026-01-01T00:00:00+00:00"})
    with pytest.raises(drf_serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_batch_query_allows_omitted_window():
    serializer = BackupBatchQuerySerializer(data={"cluster_id": 1})
    assert serializer.is_valid(), serializer.errors


# --- view wiring ------------------------------------------------------------------------------


def test_list_batches_view_does_not_reapply_swagger():
    """Class-level + method-level swagger_auto_schema used to 500 on every list_batches call."""
    from rest_framework.permissions import AllowAny
    from rest_framework.test import APIRequestFactory

    from backend.db_services.redis.rollback.views import BackupBatchViewSet

    factory = APIRequestFactory()
    request = factory.post(
        "/apis/redis/bizs/1/rollback/batches/list_batches/",
        {"cluster_id": 1, "start_time": "2026-09-20T00:00:00+08:00", "end_time": "2026-09-20T23:59:59+08:00"},
        format="json",
    )
    request.user = MagicMock(username="admin", is_authenticated=True, is_superuser=True)

    cluster = MagicMock()
    cluster.id = 1
    cluster.bk_biz_id = 1
    expected = {"locator_source": "table", "cluster_shards": [], "batches": []}
    with patch.object(BackupBatchViewSet, "permission_classes", [AllowAny]), patch.object(
        BackupBatchViewSet, "get_permissions", lambda self: []
    ), patch("backend.db_services.redis.rollback.views.Cluster.objects.get", return_value=cluster), patch(
        "backend.db_services.redis.rollback.views.BackupBatchService"
    ) as service_cls:
        service_cls.return_value.list_batches.return_value = expected
        response = BackupBatchViewSet.as_view({"post": "list_batches"}, serializer_class=BackupBatchQuerySerializer)(
            request, bk_biz_id=1
        )

    assert response.status_code == 200
    assert response.data == expected
    service_cls.return_value.list_batches.assert_called_once()


def test_batch_details_view_passes_identify_through():
    from rest_framework.permissions import AllowAny
    from rest_framework.test import APIRequestFactory

    from backend.db_services.redis.rollback.serializers import BatchDetailQuerySerializer
    from backend.db_services.redis.rollback.views import BackupBatchViewSet

    factory = APIRequestFactory()
    request = factory.post(
        "/apis/redis/bizs/1/rollback/batches/batch_details/",
        {"cluster_id": 1, "backup_identify": "SCHEDULED-2026010101"},
        format="json",
    )
    request.user = MagicMock(username="admin", is_authenticated=True, is_superuser=True)

    cluster = MagicMock()
    expected = {"locator_source": "table", "backup_identify": "SCHEDULED-2026010101", "shards": []}
    with patch.object(BackupBatchViewSet, "permission_classes", [AllowAny]), patch.object(
        BackupBatchViewSet, "get_permissions", lambda self: []
    ), patch("backend.db_services.redis.rollback.views.Cluster.objects.get", return_value=cluster), patch(
        "backend.db_services.redis.rollback.views.BackupBatchService"
    ) as service_cls:
        service_cls.return_value.batch_details.return_value = expected
        response = BackupBatchViewSet.as_view({"post": "batch_details"}, serializer_class=BatchDetailQuerySerializer)(
            request, bk_biz_id=1
        )

    assert response.status_code == 200
    assert response.data == expected
    service_cls.return_value.batch_details.assert_called_once_with(
        backup_identify="SCHEDULED-2026010101", shard_values=None
    )
