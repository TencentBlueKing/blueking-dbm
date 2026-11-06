# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

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


_CLUSTER_NODES = "\n".join(
    [
        "m1 1.1.1.1:30000@40000 myself,master - 0 0 1 connected 0-5460",
        "m2 1.1.1.2:30000@40000 master - 0 0 2 connected 5461-10922 [10923->-m3]",
        "m3 1.1.1.3:30000@40000 master - 0 0 3 connected 10923-16383",
        "s1 2.2.2.1:30000@40000 slave m1 0 0 1 connected",
        "s2 2.2.2.2:30000@40000 slave m2 0 0 2 connected",
        "",
    ]
)


def _cluster_protocol_cluster(cluster_type=ClusterType.TendisPredixyTendisplusCluster.value):
    cluster = MagicMock()
    cluster.id = 1
    cluster.bk_cloud_id = 0
    cluster.cluster_type = cluster_type
    cluster.nosqlstoragesetdtl_set.filter.return_value.first.return_value = None
    node = MagicMock(ip_port="2.2.2.1:30000")
    cluster.storageinstance_set.filter.return_value.filter.return_value.first.return_value = node
    cluster.storageinstance_set.filter.return_value.__iter__.side_effect = lambda: iter([_master()])
    return cluster


@pytest.fixture
def cluster_password():
    with patch(
        "backend.db_services.redis.rollback.shards.PayloadHandler.redis_get_cluster_password",
        return_value={"redis_password": "pwd"},
    ) as password:
        yield password


@pytest.mark.parametrize(
    "cluster_type", [ClusterType.TendisPredixyTendisplusCluster.value, ClusterType.TendisPredixyRedisCluster.value]
)
def test_resolver_cluster_protocol_reads_live_cluster_nodes(cluster_type, cluster_password):
    with patch(
        "backend.db_services.redis.rollback.shards.DRSApi.redis_rpc",
        return_value=[{"address": "2.2.2.1:30000", "result": _CLUSTER_NODES}],
    ) as rpc:
        refs = ShardResolver(_cluster_protocol_cluster(cluster_type)).from_db_meta()

    params = rpc.call_args.args[0]
    assert (params["addresses"], params["command"], params["password"]) == (["2.2.2.1:30000"], "cluster nodes", "pwd")
    assert [(r.shard_value, r.current_master, r.current_slave, r.resolvable) for r in refs] == [
        ("0-5460", "1.1.1.1:30000", "2.2.2.1:30000", True),
        ("5461-10922 [10923->-m3]", "1.1.1.2:30000", "2.2.2.2:30000", True),
        ("10923-16383", "1.1.1.3:30000", None, True),
    ]
    assert all(r.warning == "" for r in refs)


def test_resolver_cluster_nodes_are_fetched_once_per_resolver(cluster_password):
    resolver = ShardResolver(_cluster_protocol_cluster())
    with patch(
        "backend.db_services.redis.rollback.shards.DRSApi.redis_rpc",
        return_value=[{"address": "2.2.2.1:30000", "result": _CLUSTER_NODES}],
    ) as rpc:
        resolver.from_db_meta()
        resolver.cluster_shard_map()
        refs = resolver.from_backup_records([{"shard_value": "0-5460", "source_ip": "2.2.2.1", "server_port": 30000}])
    assert rpc.call_count == 1
    assert (refs[0].current_master, refs[0].current_slave) == ("1.1.1.1:30000", "2.2.2.1:30000")


@pytest.mark.parametrize(
    "rpc_kwargs",
    [
        {"side_effect": RuntimeError("drs timeout")},
        {"return_value": []},
        {"return_value": [{"address": "2.2.2.1:30000", "result": "s1 2.2.2.1:30000@40000 slave m1 0 0 1 connected"}]},
    ],
)
def test_resolver_cluster_protocol_falls_back_to_db_meta(rpc_kwargs, cluster_password):
    with patch("backend.db_services.redis.rollback.shards.DRSApi.redis_rpc", **rpc_kwargs):
        refs = ShardResolver(_cluster_protocol_cluster()).from_db_meta()
    assert len(refs) == 1
    assert refs[0].shard_value == ""
    assert refs[0].resolvable is False
    assert refs[0].current_master == "1.1.1.1:30000"
    assert "降级读取 db_meta" in refs[0].warning and "2.2.2.1:30000" in refs[0].warning


def test_resolver_cluster_protocol_falls_back_when_password_lookup_fails():
    with patch(
        "backend.db_services.redis.rollback.shards.PayloadHandler.redis_get_cluster_password",
        side_effect=RuntimeError("dbconfig down"),
    ), patch("backend.db_services.redis.rollback.shards.DRSApi.redis_rpc") as rpc:
        refs = ShardResolver(_cluster_protocol_cluster()).from_db_meta()
    rpc.assert_not_called()
    assert refs[0].resolvable is False and "dbconfig down" in refs[0].warning


def test_resolver_non_cluster_protocol_never_calls_drs():
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    dtl = MagicMock()
    dtl.seg_range = "0-104999"
    cluster.nosqlstoragesetdtl_set.filter.return_value.first.return_value = dtl
    cluster.storageinstance_set.filter.return_value = [_master()]
    with patch("backend.db_services.redis.rollback.shards.DRSApi.redis_rpc") as rpc:
        ShardResolver(cluster).from_db_meta()
    rpc.assert_not_called()


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
