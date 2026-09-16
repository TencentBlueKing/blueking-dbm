# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from backend.db_services.redis.rollback.batches import BackupBatchService
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


def test_list_batches_filters_by_shard_value():
    cluster = MagicMock()
    cluster.immute_domain = "cache.example.db"
    service = BackupBatchService(cluster)
    service.locator.list_full_in_window = MagicMock(
        return_value=[
            _record("0-104999", "old.aof.zst", source_ip="3.3.3.3", size=10),
            _record("105000-209999", "cur.aof.zst", server_port=30001, size=11),
        ]
    )
    service.resolver.from_db_meta = MagicMock(
        return_value=[
            ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True),
            ShardRef("105000-209999", current_master="1.1.1.1:30001", current_slave="1.1.1.9:30001", resolvable=True),
        ]
    )
    service.resolver.cluster_shard_map = MagicMock(return_value=[])

    result = service.list_batches(shard_values=["0-104999"])
    batch = result["batches"][0]
    assert [s["shard_value"] for s in batch["shards"]] == ["0-104999"]
    round_detail = batch["shards"][0]["rounds"][0]
    assert round_detail["source_ip"] == "3.3.3.3"
    assert round_detail["source_is_current"] is False
    assert batch["shards"][0]["in_current_topology"] is True


def test_list_batches_groups_rounds_per_shard():
    cluster = MagicMock()
    service = BackupBatchService(cluster)
    service.locator.list_full_in_window = MagicMock(
        return_value=[
            _record("0-1", "r1.aof.zst", minute="00"),
            _record("0-1", "r2.aof.zst", minute="20"),
        ]
    )
    service.resolver.from_db_meta = MagicMock(return_value=[])
    service.resolver.cluster_shard_map = MagicMock(return_value=[])

    batch = service.list_batches()["batches"][0]

    assert batch["has_multi_rounds"] is True
    assert batch["backup_type"] == "SCHEDULED"
    assert batch["shard_count"] == 1
    rounds = batch["shards"][0]["rounds"]
    assert [r["round_key"] for r in rounds] == ["r2.aof.zst", "r1.aof.zst"]
    assert rounds[0]["is_latest"] is True
    assert rounds[1]["is_latest"] is False


def test_list_batches_marks_shard_absent_from_topology():
    cluster = MagicMock()
    service = BackupBatchService(cluster)
    service.locator.list_full_in_window = MagicMock(return_value=[_record("0-104999", "a.aof.zst")])
    service.resolver.from_db_meta = MagicMock(return_value=[])
    service.resolver.cluster_shard_map = MagicMock(return_value=[])

    shard = service.list_batches()["batches"][0]["shards"][0]

    assert shard["in_current_topology"] is False
    assert shard["current_master"] is None


def test_list_batches_round_keeps_all_split_files():
    cluster = MagicMock()
    service = BackupBatchService(cluster)
    service.locator.list_full_in_window = MagicMock(
        return_value=[
            dict(_record("0-1", "full.aof.zst.split.000", size=5), round_key="full.aof.zst"),
            dict(_record("0-1", "full.aof.zst.split.001", size=7), round_key="full.aof.zst"),
        ]
    )
    service.resolver.from_db_meta = MagicMock(return_value=[])
    service.resolver.cluster_shard_map = MagicMock(return_value=[])

    rounds = service.list_batches()["batches"][0]["shards"][0]["rounds"]

    assert len(rounds) == 1
    assert rounds[0]["is_complete"] is True
    assert rounds[0]["size"] == 12
    assert len(rounds[0]["files"]) == 2
