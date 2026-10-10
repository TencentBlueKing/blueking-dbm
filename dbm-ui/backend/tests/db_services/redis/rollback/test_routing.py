# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.routing import ShardRouter
from backend.db_services.redis.rollback.serializers import ShardRouteSerializer
from backend.db_services.redis.rollback.shards import ShardRef

TWEMPROXY_SHARDS = [
    ShardRef("0-209999", current_master="1.1.1.1:30000", current_slave="2.2.2.2:30000"),
    ShardRef("210000-419999", current_master="1.1.1.1:30001", current_slave="2.2.2.2:30001"),
]

CLUSTER_NODES = "\n".join(
    [
        "a1 1.1.1.1:30000@40000 myself,master - 0 0 1 connected 0-8191",
        "a2 1.1.1.1:30001@40001 master - 0 0 2 connected 8192-10000 10002-16383",
        "a3 2.2.2.2:30000@40000 slave a1 0 0 1 connected",
        "",
    ]
)

GETSERVER_REPLIES = {
    "user:1": "1.1.1.1:30000:1 route-app 0-209999 1",
    "user:2": "1.1.1.1:30001:1 route-app 210000-419999 1\n",
    # Backends absent from db_meta are reported as is.
    "low": "3.3.3.3:30009:1 route-app 0-500 1",
}


def _cluster(cluster_type):
    cluster = MagicMock()
    cluster.id = 1
    cluster.immute_domain = "route.example.db"
    cluster.cluster_type = cluster_type
    cluster.bk_cloud_id = 0
    proxy = SimpleNamespace(ip_port="3.3.3.3:50000")
    cluster.proxyinstance_set.filter.return_value.first.return_value = proxy
    return cluster


def _storages(cluster, slave=None, master="1.1.1.1:30000"):
    def by_role(instance_role, **_):
        address = slave if instance_role == InstanceRole.REDIS_SLAVE.value else master
        found = MagicMock()
        found.first.return_value = SimpleNamespace(ip_port=address) if address else None
        found.filter.return_value = found
        return found

    cluster.storageinstance_set.filter.side_effect = by_role


def _router(cluster_type, shards, rpc, slave="2.2.2.2:30000"):
    cluster = _cluster(cluster_type)
    _storages(cluster, slave=slave)
    router = ShardRouter(cluster)
    router.resolver.from_db_meta = MagicMock(return_value=shards)
    router._rpc = MagicMock(side_effect=rpc)
    return router


@pytest.fixture(autouse=True)
def passwords():
    with patch(
        "backend.db_services.redis.rollback.routing.PayloadHandler.redis_get_cluster_password",
        return_value={"redis_password": "p", "redis_proxy_password": "pp"},
    ):
        yield


@pytest.fixture
def batch():
    """Set the full-backup records of the batch the router looks up."""
    with patch("backend.db_services.redis.rollback.routing.BackupLocator") as locator:

        def _set(*shard_values):
            locator.return_value.locate_full_by_identify.return_value = [
                {"shard_value": value, "source_ip": "1.1.1.9", "server_port": 30000 + index}
                for index, value in enumerate(shard_values)
            ]
            return locator

        yield _set


def _twemproxy_rpc(address, password, command):
    assert (address, password) == ("3.3.3.3:50000", "pp")
    key = command.split(" ", 1)[1]
    if key == "boom":
        raise RuntimeError("drs timeout")
    return GETSERVER_REPLIES.get(key, "garbage")


def _twemproxy():
    return _router(ClusterType.TendisTwemproxyRedisInstance.value, TWEMPROXY_SHARDS, _twemproxy_rpc)


def _by_key(result):
    return {r["key"]: r for r in result["results"]}


def test_twemproxy_returns_raw_getserver_range_without_batch():
    router = _twemproxy()
    result = router.route(["user:1", "user:2", "low", "user:1"])

    assert result == {
        "results": [
            {"key": "user:1", "range": "0-209999", "backend": "1.1.1.1:30000", "error": ""},
            {"key": "user:2", "range": "210000-419999", "backend": "1.1.1.1:30001", "error": ""},
            {"key": "low", "range": "0-500", "backend": "3.3.3.3:30009", "error": ""},
        ]
    }
    assert [call.args[2] for call in router._rpc.call_args_list] == [
        "getserver user:1",
        "getserver user:2",
        "getserver low",
    ]


def test_merged_current_shard_returns_every_split_batch_shard(batch):
    locator = batch("0-209999", "315000-419999", "210000-314999")
    result = _twemproxy().route(["user:2"], backup_identify="SCHEDULED-1")

    locator.return_value.locate_full_by_identify.assert_called_once_with("SCHEDULED-1")
    key = result["results"][0]
    assert key["batch_shard_values"] == ["210000-314999", "315000-419999"]
    assert key["is_covered"] is True and key["uncovered_ranges"] == []
    assert result["batch_shard_values"] == ["210000-314999", "315000-419999"]
    assert result["warnings"] == []


def test_range_covered_by_several_batch_shards(batch):
    batch("0-400", "401-499", "500-555", "556-419999")
    key = _twemproxy().route(["low"], backup_identify="SCHEDULED-1")["results"][0]

    assert key["batch_shard_values"] == ["0-400", "401-499", "500-555"]
    assert key["is_covered"] is True and key["uncovered_ranges"] == []


def test_batch_gap_is_reported_but_not_an_error(batch):
    batch("0-400", "500-555")
    result = _twemproxy().route(["low"], backup_identify="SCHEDULED-1")

    key = result["results"][0]
    assert key["batch_shard_values"] == ["0-400", "500-555"]
    assert key["is_covered"] is False
    assert key["uncovered_ranges"] == ["401-499"]
    assert key["error"] == ""
    assert result["batch_shard_values"] == ["0-400", "500-555"]


def test_unparseable_batch_shard_goes_to_warnings(batch):
    batch("switched-0", "0-209999", "", "switched-0", "210000-419999")
    result = _twemproxy().route(["user:1", "user:2"], backup_identify="SCHEDULED-1")

    assert len(result["warnings"]) == 2
    assert all("switched-0" in warning for warning in result["warnings"])
    assert "1.1.1.9:30000" in result["warnings"][0] and "1.1.1.9:30003" in result["warnings"][1]
    assert result["batch_shard_values"] == ["0-209999", "210000-419999"]


def test_failed_keys_get_no_batch_shards(batch):
    batch("0-209999", "210000-419999")
    results = _by_key(_twemproxy().route(["user:1", "other", "a b"], backup_identify="SCHEDULED-1"))

    assert results["user:1"]["batch_shard_values"] == ["0-209999"]
    for key in ("other", "a b"):
        assert results[key]["error"]
        assert results[key]["batch_shard_values"] == [] and results[key]["is_covered"] is False
        assert results[key]["uncovered_ranges"] == []


def _cluster_rpc(slots):
    def rpc(address, password, command):
        assert (address, password) == ("2.2.2.2:30000", "p")
        if command == "cluster nodes":
            return CLUSTER_NODES
        return slots[command.split(" ", 2)[2]] + "\n"

    return rpc


def test_cluster_protocol_routes_by_keyslot_on_a_replica():
    rpc = _cluster_rpc({"k1": "100", "k2": "10001", "k3": "12000"})
    router = _router(ClusterType.TendisPredixyTendisplusCluster.value, TWEMPROXY_SHARDS, rpc)
    results = _by_key(router.route(["k1", "k2", "k3"]))

    assert (results["k1"]["range"], results["k1"]["backend"]) == ("0-8191", "1.1.1.1:30000")
    assert (results["k3"]["range"], results["k3"]["backend"]) == ("8192-10000 10002-16383", "1.1.1.1:30001")
    assert results["k2"]["range"] == "" and "10001" in results["k2"]["error"]
    assert router._rpc.call_args_list[0].args[2] == "cluster nodes"


def test_cluster_protocol_matches_batch_by_slot_after_migration(batch):
    # The current owner "8192-10000 10002-16383" overlaps two batch shards; the slot picks one.
    batch("0-8191", "8192-11999", "12000-16383")
    rpc = _cluster_rpc({"k3": "12000"})
    router = _router(ClusterType.TendisPredixyTendisplusCluster.value, TWEMPROXY_SHARDS, rpc)
    key = router.route(["k3"], backup_identify="SCHEDULED-1")["results"][0]

    assert key["range"] == "8192-10000 10002-16383"
    assert key["batch_shard_values"] == ["12000-16383"]
    assert key["is_covered"] is True and key["uncovered_ranges"] == []


def test_cluster_protocol_slot_missing_from_batch(batch):
    batch("0-8191", "8192-11999")
    rpc = _cluster_rpc({"k3": "12000"})
    router = _router(ClusterType.TendisPredixyRedisCluster.value, TWEMPROXY_SHARDS, rpc)
    key = router.route(["k3"], backup_identify="SCHEDULED-1")["results"][0]

    assert key["batch_shard_values"] == []
    assert key["is_covered"] is False and key["uncovered_ranges"] == ["12000"]


def test_cluster_protocol_falls_back_to_master_without_replicas():
    def rpc(address, password, command):
        assert address == "1.1.1.1:30000"
        return CLUSTER_NODES if command == "cluster nodes" else "100"

    router = _router(ClusterType.TendisPredixyRedisCluster.value, TWEMPROXY_SHARDS, rpc, slave=None)
    assert router.route(["k1"])["results"][0]["range"] == "0-8191"


def test_single_shard_cluster_does_not_call_drs():
    only = [ShardRef("0-419999", current_master="1.1.1.1:30000")]
    router = _router(ClusterType.TendisRedisInstance.value, only, AssertionError)
    result = router.route(["a", "b"])

    router._rpc.assert_not_called()
    assert [(r["range"], r["backend"]) for r in result["results"]] == [("0-419999", "1.1.1.1:30000")] * 2


def test_single_shard_with_batch_returns_every_batch_shard(batch):
    batch("0-419999", "switched-0")
    only = [ShardRef("0-419999", current_master="1.1.1.1:30000")]
    result = _router(ClusterType.TendisRedisInstance.value, only, AssertionError).route(
        ["a"], backup_identify="SCHEDULED-1"
    )

    key = result["results"][0]
    assert key["batch_shard_values"] == ["0-419999"] and key["is_covered"] is True
    assert result["batch_shard_values"] == ["0-419999"]
    assert len(result["warnings"]) == 1


def test_one_failing_key_does_not_affect_the_others():
    results = _by_key(_twemproxy().route(["user:1", "boom", "other"]))

    assert results["user:1"]["range"] == "0-209999" and not results["user:1"]["error"]
    assert "drs timeout" in results["boom"]["error"]
    assert "无法解析" in results["other"]["error"]


def test_drs_down_for_every_key_fails_the_request():
    def rpc(*_):
        raise RuntimeError("connection refused")

    router = _router(ClusterType.TendisTwemproxyRedisInstance.value, TWEMPROXY_SHARDS, rpc)
    with pytest.raises(RollbackPlanError) as exc:
        router.route(["a", "b"])
    assert "connection refused" in exc.value.message


def test_cluster_nodes_failure_fails_the_request():
    def rpc(*_):
        raise RuntimeError("drs unavailable")

    router = _router(ClusterType.TendisPredixyRedisCluster.value, TWEMPROXY_SHARDS, rpc)
    with pytest.raises(RollbackPlanError) as exc:
        router.route(["a"])
    assert "drs unavailable" in exc.value.message


def test_keys_with_whitespace_or_quotes_are_reported_and_not_sent():
    router = _twemproxy()
    results = _by_key(router.route(["user:1", "a b", "tab\tkey", 'q"k', ""]))

    for key in ("a b", "tab\tkey", 'q"k', ""):
        assert results[key]["error"] and not results[key]["range"]
    assert [call.args[2] for call in router._rpc.call_args_list] == ["getserver user:1"]


def test_more_than_fifty_keys_are_rejected():
    serializer = ShardRouteSerializer(data={"cluster_id": 1, "keys": ["k{}".format(i) for i in range(51)]})
    assert not serializer.is_valid()
    assert "keys" in serializer.errors

    deduped = ShardRouteSerializer(data={"cluster_id": 1, "keys": ["k{}".format(i % 50) for i in range(80)]})
    assert deduped.is_valid(), deduped.errors
    assert len(deduped.validated_data["keys"]) == 50

    with pytest.raises(RollbackPlanError):
        _twemproxy().route(["k{}".format(i) for i in range(51)])


def test_whitespace_key_survives_serializer_so_it_can_be_reported():
    serializer = ShardRouteSerializer(data={"cluster_id": 1, "keys": [" padded ", "a b"]})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["keys"] == [" padded ", "a b"]
