# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import LOCATOR_SOURCE_BKLOG, LOCATOR_SOURCE_TABLE
from backend.db_services.redis.rollback.locator import BackupLocator, row_to_backup_system_format


def test_row_to_backup_system_format_from_dict():
    record = row_to_backup_system_format(
        {
            "backup_tag": "REDIS_FULL",
            "status": "to_backup_system_success",
            "end_time": "2026-01-01T02:00:00+00:00",
            "start_time": "2026-01-01T01:00:00+00:00",
            "backup_file_size": 128,
            "server_ip": "1.1.1.1",
            "server_port": 30000,
            "backup_taskid": "task-1",
            "backup_file": "/data/dbbak/foo.aof.zst",
            "shard_value": "0-104999",
            "backup_identify": "SCHEDULED-2026010101",
        }
    )
    assert record["file_name"] == "foo.aof.zst"
    assert record["source_ip"] == "1.1.1.1"
    assert record["task_id"] == "task-1"
    assert record["round_key"] == "foo.aof.zst"
    assert record["shard_value"] == "0-104999"


def test_locator_falls_back_to_bklog_when_table_empty():
    cluster = MagicMock()
    cluster.immute_domain = "cache.example.db"
    locator = BackupLocator(cluster)
    with patch.object(locator, "_query_table", return_value=None), patch.object(
        locator, "_query_bklog", return_value=[{"task_id": "x", "shard_value": "0-1"}]
    ) as bklog:
        records = locator.locate_full_by_identify("SCHEDULED-1")
        bklog.assert_called_once()
        assert records[0]["task_id"] == "x"
        assert locator.locator_source == LOCATOR_SOURCE_BKLOG


def test_locator_uses_table_when_hit():
    cluster = MagicMock()
    cluster.immute_domain = "cache.example.db"
    locator = BackupLocator(cluster)
    with patch.object(
        locator,
        "_query_table",
        return_value=[{"task_id": "t", "shard_value": "0-1", "file_name": "a.aof.zst"}],
    ), patch.object(locator, "_query_bklog") as bklog:
        records = locator.locate_full_by_identify("SCHEDULED-1")
        bklog.assert_not_called()
        assert records[0]["task_id"] == "t"
        assert locator.locator_source == LOCATOR_SOURCE_TABLE


def test_cache_cluster_type_constant_matches_meta():
    from backend.db_services.redis.rollback.constants import CACHE_CLUSTER_TYPES

    assert ClusterType.TendisTwemproxyRedisInstance.value in CACHE_CLUSTER_TYPES
    assert ClusterType.TendisRedisInstance.value in CACHE_CLUSTER_TYPES
    assert ClusterType.TwemproxyTendisSSDInstance.value not in CACHE_CLUSTER_TYPES
