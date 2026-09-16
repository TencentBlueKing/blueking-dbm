# -*- coding: utf-8 -*-
from backend.db_services.redis.rollback.batches import is_split_round_complete, latest_round_per_shard
from backend.db_services.redis.rollback.constants import FILTER_MODE_DELETE_MATCHED, FILTER_MODE_KEEP_MATCHED
from backend.db_services.redis.rollback.shards import ShardRef
from backend.flow.consts import DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    FullBackupRef,
    KeyFilterSpec,
    RollbackItem,
    RollbackPlan,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner


def test_split_round_complete_consecutive():
    files = [
        {"file_name": "full.split.000"},
        {"file_name": "full.split.001"},
        {"file_name": "full.split.002"},
    ]
    assert is_split_round_complete(files) is True


def test_split_round_incomplete_missing_index():
    files = [
        {"file_name": "full.split.000"},
        {"file_name": "full.split.002"},
    ]
    assert is_split_round_complete(files) is False


def test_non_split_round_complete():
    assert is_split_round_complete([{"file_name": "full.aof.zst"}]) is True


def test_mixed_split_and_nonsplit_is_incomplete():
    files = [
        {"file_name": "full.aof.zst"},
        {"file_name": "full.split.000"},
    ]
    assert is_split_round_complete(files) is False


def test_latest_round_per_shard_picks_newest_begin():
    records = [
        {
            "shard_value": "0-104999",
            "round_key": "a",
            "backup_begin_time": "2026-01-01T01:00:00+00:00",
            "file_name": "a.aof.zst",
        },
        {
            "shard_value": "0-104999",
            "round_key": "b",
            "backup_begin_time": "2026-01-01T02:00:00+00:00",
            "file_name": "b.aof.zst",
        },
    ]
    latest = latest_round_per_shard(records)
    assert list(latest.keys()) == ["0-104999"]
    assert latest["0-104999"][0]["round_key"] == "b"


def test_key_filter_spec_routing():
    assert KeyFilterSpec.from_ticket("", "").enabled is False
    keep = KeyFilterSpec.from_ticket("user:*", "tmp:*")
    assert keep.filter_mode == FILTER_MODE_KEEP_MATCHED
    delete_only_black = KeyFilterSpec.from_ticket("", "tmp:*")
    assert delete_only_black.filter_mode == FILTER_MODE_DELETE_MATCHED
    assert delete_only_black.white_regex == ".*"


def test_pack_dest_hosts_keeps_same_source_adjacent():
    items = [
        RollbackItem(
            shard=ShardRef(shard_value="0-1"),
            source_ip="1.1.1.1",
            source_port=30000,
            source_is_current=True,
            dest_ip="",
            dest_port=0,
            full_files=[FullBackupRef("t1", "f1", 10, "1.1.1.1", 30000, "0-1", "id", "", "", "f1")],
        ),
        RollbackItem(
            shard=ShardRef(shard_value="2-3"),
            source_ip="1.1.1.9",
            source_port=30000,
            source_is_current=True,
            dest_ip="",
            dest_port=0,
            full_files=[FullBackupRef("t2", "f2", 20, "1.1.1.9", 30000, "2-3", "id", "", "", "f2")],
        ),
        RollbackItem(
            shard=ShardRef(shard_value="4-5"),
            source_ip="1.1.1.1",
            source_port=30001,
            source_is_current=True,
            dest_ip="",
            dest_port=0,
            full_files=[FullBackupRef("t3", "f3", 30, "1.1.1.1", 30001, "4-5", "id", "", "", "f3")],
        ),
    ]
    plan = RollbackPlan(
        cluster_id=1,
        immute_domain="cache.example.db",
        cluster_type="TwemproxyRedisInstance",
        tendis_type="RedisInstance",
        bk_cloud_id=0,
        bk_biz_id=1,
        db_version="Redis-6",
        proxy_port=50000,
        items=items,
    )
    planner = RollbackPlanner.__new__(RollbackPlanner)
    planner._pack_dest_hosts(plan, ["2.2.2.2"], 1)
    assert [item.dest_port for item in plan.items] == [
        DEFAULT_REDIS_START_PORT,
        DEFAULT_REDIS_START_PORT + 1,
        DEFAULT_REDIS_START_PORT + 2,
    ]
    assert [item.source_ip for item in plan.items] == ["1.1.1.1", "1.1.1.1", "1.1.1.9"]
    assert plan.dest_hosts[0].download_bytes == 60
    assert plan.dest_hosts[0].ports == [
        DEFAULT_REDIS_START_PORT,
        DEFAULT_REDIS_START_PORT + 1,
        DEFAULT_REDIS_START_PORT + 2,
    ]
