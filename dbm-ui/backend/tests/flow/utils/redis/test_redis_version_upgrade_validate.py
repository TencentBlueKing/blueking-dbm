# -*- coding: utf-8 -*-
"""主从版版本升级 pair/IP 维度校验 helper 测试

这套规则被"原地升级"和"整机替换升级"共用: 两者都会做主从切换, 所以对
"同一 IP 对上的集群必须整体升级、且目标版本一致" 的要求完全相同。
"""
from types import SimpleNamespace

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.redis import redis_version_upgrade_validate as mod

MASTER_IP = "1.1.1.1"
SLAVE_IP = "1.1.1.2"
TARGET_VERSION = "redis-6.2.14"
CURRENT_VERSION = "redis-5.0.9"


class _FakeQuery:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


class _FakeStorageInstance:
    def __init__(self, ip, receiver=None):
        self.machine = SimpleNamespace(ip=ip)
        self.ip_port = "{}:30000".format(ip)
        self.as_ejector = _FakeQuery(SimpleNamespace(receiver=receiver) if receiver else None)


class _FakeStorageInstanceSet:
    def __init__(self, master):
        self.master = master

    def filter(self, **kwargs):
        if kwargs.get("instance_role") == InstanceRole.REDIS_MASTER.value:
            return _FakeQuery(self.master)
        return _FakeQuery(None)


def _fake_cluster(cluster_id=1, master_ip=MASTER_IP, slave_ip=SLAVE_IP):
    cluster = SimpleNamespace(
        id=cluster_id,
        cluster_type=ClusterType.TendisRedisInstance,
        immute_domain="cache-{}.test.db".format(cluster_id),
    )
    cluster.storageinstance_set = _FakeStorageInstanceSet(
        _FakeStorageInstance(master_ip, receiver=_FakeStorageInstance(slave_ip))
    )
    return cluster


class _FakeStorageObjects:
    """(ip, role) -> cluster_ids, 模拟 StorageInstance.objects 的角色反查"""

    def __init__(self, ip_role_clusters):
        self.ip_role_clusters = ip_role_clusters

    def filter(self, **kwargs):
        key = (kwargs["machine__ip"], kwargs["instance_role"])
        cluster_ids = self.ip_role_clusters.get(key, set())
        return SimpleNamespace(values_list=lambda *args, **kw: list(cluster_ids))


def _stub_db(monkeypatch, ip_role_clusters, valid_versions=None, current_version=CURRENT_VERSION):
    monkeypatch.setattr(mod.StorageInstance, "objects", _FakeStorageObjects(ip_role_clusters))
    monkeypatch.setattr(
        mod, "get_storage_version_names_by_cluster_type", lambda *a, **kw: valid_versions or [TARGET_VERSION]
    )
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *a, **kw: current_version)


def _register(clusters_and_ips):
    pair_buckets, ip_index, cluster_meta = {}, {}, {}
    for cluster, target_version, ips in clusters_and_ips:
        mod.register_pair_entry(
            cluster=cluster,
            target_version=target_version,
            ips_in_item=set(ips),
            pair_buckets=pair_buckets,
            ip_index=ip_index,
            cluster_meta=cluster_meta,
        )
    return pair_buckets, ip_index, cluster_meta


def test_get_master_slave_ips():
    assert mod.get_master_slave_ips(_fake_cluster()) == (MASTER_IP, SLAVE_IP)


def test_register_rejects_ip_outside_the_pair():
    with pytest.raises(Exception, match="不属于该集群的主从对"):
        _register([(_fake_cluster(), TARGET_VERSION, [SLAVE_IP, "2.2.2.2"])])


def test_register_requires_slave_ip():
    with pytest.raises(Exception, match="必须包含 slave_ip"):
        _register([(_fake_cluster(), TARGET_VERSION, [MASTER_IP])])


def test_register_merges_sibling_clusters_into_one_bucket():
    pair_buckets, ip_index, cluster_meta = _register(
        [
            (_fake_cluster(1), TARGET_VERSION, [SLAVE_IP]),
            (_fake_cluster(2), TARGET_VERSION, [SLAVE_IP]),
        ]
    )

    assert list(pair_buckets) == [(MASTER_IP, SLAVE_IP)]
    assert pair_buckets[(MASTER_IP, SLAVE_IP)]["cluster_ids"] == [1, 2]
    assert ip_index[MASTER_IP]["as_master_cluster_ids"] == {1, 2}
    assert ip_index[SLAVE_IP]["as_slave_cluster_ids"] == {1, 2}
    assert cluster_meta[1]["upgrade_master"] is False


def test_validate_noop_without_buckets():
    mod.validate_pair_buckets(pair_buckets={}, ip_index={}, cluster_meta={})


def test_validate_finalizes_bucket(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(), TARGET_VERSION, [MASTER_IP, SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
    )

    mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)

    bucket = pair_buckets[(MASTER_IP, SLAVE_IP)]
    assert bucket["target_version"] == TARGET_VERSION
    assert bucket["upgrade_master"] is True
    assert "target_versions" not in bucket
    assert "upgrade_master_flags" not in bucket


def test_validate_rejects_missing_sibling_cluster(monkeypatch):
    """漏提交兄弟集群会让同一台机器同时承载 master 和 slave 实例"""
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(1), TARGET_VERSION, [SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1, 2},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
    )

    with pytest.raises(Exception, match="未加入本次升级"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_inconsistent_target_versions_on_one_ip(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register(
        [
            (_fake_cluster(1), TARGET_VERSION, [SLAVE_IP]),
            (_fake_cluster(2), "redis-7.0.0", [SLAVE_IP]),
        ]
    )
    _stub_db(monkeypatch, {})

    with pytest.raises(Exception, match="目标版本不一致"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_inconsistent_upgrade_scope(monkeypatch):
    """同 pair 上一个集群只升 slave、另一个连 master 一起升, 切换动作会互相打断"""
    pair_buckets, ip_index, cluster_meta = _register(
        [
            (_fake_cluster(1), TARGET_VERSION, [SLAVE_IP]),
            (_fake_cluster(2), TARGET_VERSION, [MASTER_IP, SLAVE_IP]),
        ]
    )
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1, 2},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1, 2},
        },
    )

    with pytest.raises(Exception, match="升级范围不一致"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_multiple_pair_partners(monkeypatch):
    """一台机器出现在两种主从配对里, 拓扑不被支持"""
    pair_buckets, ip_index, cluster_meta = _register(
        [
            (_fake_cluster(1), TARGET_VERSION, [SLAVE_IP]),
            (_fake_cluster(2, master_ip=MASTER_IP, slave_ip="3.3.3.3"), TARGET_VERSION, ["3.3.3.3"]),
        ]
    )
    _stub_db(monkeypatch, {})

    with pytest.raises(Exception, match="存在多种主从配对"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_unsupported_target_version(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(), "bad-version", [SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
    )

    with pytest.raises(Exception, match="目标版本 bad-version 不合法"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_downgrade(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(), TARGET_VERSION, [SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
        current_version="redis-7.0.0",
    )

    with pytest.raises(Exception, match="不支持降级"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_redis_to_valkey(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(), "valkey-8.0.1", [SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
        valid_versions=["valkey-8.0.1"],
        current_version="redis-6.2.14",
    )

    with pytest.raises(Exception, match="请使用 DTS 数据迁移"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)


def test_validate_rejects_valkey_to_redis(monkeypatch):
    pair_buckets, ip_index, cluster_meta = _register([(_fake_cluster(), "redis-7.2.4", [SLAVE_IP])])
    _stub_db(
        monkeypatch,
        {
            (MASTER_IP, InstanceRole.REDIS_MASTER.value): {1},
            (SLAVE_IP, InstanceRole.REDIS_SLAVE.value): {1},
        },
        valid_versions=["redis-7.2.4"],
        current_version="valkey-8.0.1",
    )

    with pytest.raises(Exception, match="请使用 DTS 数据迁移"):
        mod.validate_pair_buckets(pair_buckets, ip_index, cluster_meta)
