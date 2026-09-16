# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import (
    IDENTIFY_UNKNOWN,
    SINGLE_INSTANCE_SHARD_VALUE,
    SWITCHED_SHARD_VALUE,
)
from backend.db_services.redis.rollback.shards import (
    ShardResolver,
    coverage_gaps,
    extract_identify_prefix,
    overlapping_shards,
    parse_shard_value,
    round_key_from_filename,
)


def test_parse_shard_value_multi_range():
    result = parse_shard_value("1365-1637 10651-10923\n13382-13654 15020-15292 16111-16383")
    assert result.parseable
    assert result.ranges == [
        (1365, 1637),
        (10651, 10923),
        (13382, 13654),
        (15020, 15292),
        (16111, 16383),
    ]


def test_parse_shard_value_single_slots_and_ranges():
    result = parse_shard_value("1-2 4 5-6")
    assert result.parseable
    assert result.ranges == [(1, 2), (4, 4), (5, 6)]


def test_parse_shard_value_ignores_migrating_markers():
    result = parse_shard_value("[3->-node-b] 1-2 [4-<-node-a] 5-6")
    assert result.parseable
    assert result.ranges == [(1, 2), (5, 6)]


def test_parse_shard_value_switched_zero_is_unparseable():
    result = parse_shard_value(SWITCHED_SHARD_VALUE)
    assert result.parseable is False
    assert "switched-0" in result.reason


def test_parse_shard_value_non_numeric_is_unparseable():
    result = parse_shard_value("abc-def")
    assert result.parseable is False


def test_parse_shard_value_empty():
    assert parse_shard_value("").parseable is False
    assert parse_shard_value(None).parseable is False


def test_round_key_strips_split_suffix():
    assert (
        round_key_from_filename("00001-redis-slave-1.1.1.1-30000-20251215-050000.split.003")
        == "00001-redis-slave-1.1.1.1-30000-20251215-050000"
    )
    assert round_key_from_filename("foo.aof.zst") == "foo.aof.zst"


def test_extract_identify_prefix():
    assert extract_identify_prefix("SCHEDULED-2025121505") == "SCHEDULED"
    assert extract_identify_prefix("BILL123-170000") == "BILL"
    assert extract_identify_prefix("weird-id") == IDENTIFY_UNKNOWN


def test_coverage_gaps_full_twemproxy():
    shards = ["0-104999", "105000-209999", "210000-314999", "315000-419999"]
    assert coverage_gaps(shards) == []


def test_coverage_gaps_missing_last():
    shards = ["0-104999", "105000-209999", "210000-314999"]
    gaps = coverage_gaps(shards)
    assert 315000 in gaps
    assert 419999 in gaps


def test_single_instance_shard_value():
    assert SINGLE_INSTANCE_SHARD_VALUE == "0-419999"


def test_overlapping_shards_disjoint():
    assert overlapping_shards(["0-104999", "105000-209999", "210000-314999"]) == []


def test_overlapping_shards_detects_intersection():
    conflicts = overlapping_shards(["0-104999", "50000-209999"])
    assert conflicts == [("0-104999", "50000-209999")]


def test_overlapping_shards_detects_identical():
    assert overlapping_shards(["0-104999", "0-104999"]) == [("0-104999", "0-104999")]


def test_overlapping_shards_multi_range():
    conflicts = overlapping_shards(["1-2 10-20", "15-16"])
    assert conflicts == [("1-2 10-20", "15-16")]


def test_overlapping_shards_skips_unparseable():
    assert overlapping_shards([SWITCHED_SHARD_VALUE, "", "0-104999"]) == []


def _master(ip="1.1.1.1", port=30000, slave_ip="1.1.1.9"):
    master = MagicMock()
    master.machine.ip = ip
    master.port = port
    master.ip_port = "{}:{}".format(ip, port)
    slave = MagicMock()
    slave.machine.ip = slave_ip
    slave.port = port
    master.as_ejector.get.return_value.receiver = slave
    return master


def test_resolver_twemproxy_uses_seg_range():
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    dtl = MagicMock()
    dtl.seg_range = "0-104999"
    cluster.nosqlstoragesetdtl_set.filter.return_value.first.return_value = dtl
    cluster.storageinstance_set.filter.return_value = [_master()]
    refs = ShardResolver(cluster).from_db_meta()
    assert refs[0].shard_value == "0-104999"
    assert refs[0].resolvable is True
    assert refs[0].current_master == "1.1.1.1:30000"
    assert refs[0].current_slave == "1.1.1.9:30000"


def test_resolver_single_instance_fallback():
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = ClusterType.TendisRedisInstance.value
    cluster.storageinstance_set.filter.return_value = [_master()]
    refs = ShardResolver(cluster).from_db_meta()
    assert refs[0].shard_value == SINGLE_INSTANCE_SHARD_VALUE
    assert refs[0].resolvable is True


def test_resolver_switched_zero_degrades():
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    dtl = MagicMock()
    dtl.seg_range = SWITCHED_SHARD_VALUE
    cluster.nosqlstoragesetdtl_set.filter.return_value.first.return_value = dtl
    cluster.storageinstance_set.filter.return_value = [_master()]
    refs = ShardResolver(cluster).from_db_meta()
    assert refs[0].resolvable is False
    assert refs[0].shard_value == SWITCHED_SHARD_VALUE
    assert "switched-0" in refs[0].warning
