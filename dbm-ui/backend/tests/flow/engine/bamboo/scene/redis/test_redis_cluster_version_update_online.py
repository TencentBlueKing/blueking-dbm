# -*- coding: utf-8 -*-
from collections import defaultdict
from types import SimpleNamespace

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.flow.engine.bamboo.scene.redis import redis_cluster_version_update_online as mod
from backend.flow.engine.bamboo.scene.redis.redis_cluster_version_update_online import RedisClusterVersionUpdateOnline

TARGET_VERSION = "redis-6.2.14"
TARGET_MAJOR_VERSION = "Redis-6"
CURRENT_VERSION = "redis-5.0.9"
UNKNOWN_CLUSTER_IP = "not-in-cluster-ip"


class _FakeQuery:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


class _FakeStorageInstance:
    def __init__(self, ip, port, receiver=None):
        self.machine = SimpleNamespace(ip=ip)
        self.ip_port = "{}:{}".format(ip, port)
        self.as_ejector = _FakeQuery(SimpleNamespace(receiver=receiver) if receiver else None)


class _FakeStorageInstanceSet:
    def __init__(self, master):
        self.master = master

    def filter(self, **kwargs):
        if kwargs.get("instance_role") == InstanceRole.REDIS_MASTER.value:
            return _FakeQuery(self.master)
        return _FakeQuery(None)


class _FakeCluster:
    def __init__(
        self,
        cluster_id=1,
        cluster_type=ClusterType.TendisPredixyRedisCluster,
        domain=None,
        master_ip="1.1.1.1",
        slave_ip="1.1.1.2",
    ):
        self.id = cluster_id
        self.cluster_type = cluster_type
        self.immute_domain = domain or "cache-{}.test.db".format(cluster_id)
        self.bk_biz_id = 100

        slave = _FakeStorageInstance(slave_ip, 30000)
        master = _FakeStorageInstance(master_ip, 30000, receiver=slave)
        self.storageinstance_set = _FakeStorageInstanceSet(master)


class _FakeStorageObjects:
    def __init__(self, cluster_ids_by_ip_role):
        self.cluster_ids_by_ip_role = cluster_ids_by_ip_role

    def filter(self, **kwargs):
        key = (kwargs["machine__ip"], kwargs["instance_role"])
        return _FakeValuesQuery(self.cluster_ids_by_ip_role.get(key, set()))


class _FakeValuesQuery:
    def __init__(self, values):
        self.values = list(values)

    def values_list(self, *args, **kwargs):
        return self.values


class _RecorderBuilder:
    created = []

    def __init__(self, *args, **kwargs):
        self.acts = []
        self.parallel_acts = []
        self.sub_pipelines = []
        self.parallel_sub_pipelines = []
        self.sub_name = None
        self.ran = False
        _RecorderBuilder.created.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        self.acts.append(
            {
                "act_name": act_name,
                "act_component_code": act_component_code,
                "kwargs": kwargs,
                **extra,
            }
        )

    def add_parallel_acts(self, acts_list=None, **kwargs):
        self.parallel_acts.append(list(acts_list or kwargs.get("acts_list") or []))

    def add_sub_pipeline(self, sub_builder):
        self.sub_pipelines.append(sub_builder)

    def add_parallel_sub_pipeline(self, sub_flow_list=None, **kwargs):
        self.parallel_sub_pipelines.append(list(sub_flow_list or kwargs.get("sub_flow_list") or []))

    def build_sub_process(self, sub_name):
        self.sub_name = sub_name
        return {"sub_name": sub_name, "builder": self}

    def run_pipeline(self, *args, **kwargs):
        self.ran = True


def _new_flow(data=None):
    flow = object.__new__(RedisClusterVersionUpdateOnline)
    flow.root_id = "root-1"
    flow.data = data or _ticket_data()
    flow.cluster_cache = {}
    flow._cluster_objs = {}
    flow.cluster_versions_ips = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    flow.instance_pair_buckets = {}
    flow.instance_ip_index = {}
    flow.instance_cluster_meta = {}
    return flow


def _construct_flow_without_precheck(monkeypatch, data=None):
    monkeypatch.setattr(RedisClusterVersionUpdateOnline, "precheck", lambda self: None)
    return RedisClusterVersionUpdateOnline(root_id="root-1", data=data or _ticket_data())


def _ticket_data(infos=None):
    return {
        "uid": 1,
        "bk_biz_id": 100,
        "created_by": "tester",
        "ticket_type": "REDIS_VERSION_UPDATE_ONLINE",
        "infos": infos or [],
    }


def _info_item(node_type=RedisVerUpdateNodeType.Backend.value, cluster_id=1, target_versions=None):
    return {
        "cluster_id": cluster_id,
        "node_type": node_type,
        "target_versions": target_versions
        if target_versions is not None
        else [{"ip": "1.1.1.2", "version": TARGET_VERSION}],
    }


def _cluster_meta(cluster_type, cluster_id=1, master_ip="1.1.1.1", slave_ip="1.1.1.2"):
    master_ports = [30000, 30001]
    slave_ports = [30000, 30001]
    return {
        "bk_biz_id": 100,
        "bk_cloud_id": 0,
        "cluster_id": cluster_id,
        "cluster_name": "cluster-{}".format(cluster_id),
        "immute_domain": "cache-{}.test.db".format(cluster_id),
        "cluster_type": cluster_type,
        "major_version": "Redis-5",
        "redis_password": "redis-pwd",
        "master_ports": {master_ip: master_ports},
        "slave_ports": {slave_ip: slave_ports},
        "master_ip_to_slave_ip": {master_ip: slave_ip},
        "master_slave_ins_pairs": [
            {
                "master": {"ip": master_ip, "port": port},
                "slave": {"ip": slave_ip, "port": slave_ports[idx]},
            }
            for idx, port in enumerate(master_ports)
        ],
    }


def _flatten_act_names():
    names = []
    for builder in _RecorderBuilder.created:
        names.extend(act["act_name"] for act in builder.acts)
        for acts in builder.parallel_acts:
            names.extend(act["act_name"] for act in acts)
    return names


def _install_recorder_build_stubs(monkeypatch, meta_by_id, host_ports=None):
    _RecorderBuilder.created = []
    host_ports = host_ports or {}

    monkeypatch.setattr(mod, "Builder", _RecorderBuilder)
    monkeypatch.setattr(mod, "SubBuilder", _RecorderBuilder)
    monkeypatch.setattr(mod, "ClusterProxysUpgradeAtomJob", lambda *args, **kwargs: {"atom": "proxy"})
    monkeypatch.setattr(mod, "ClusterIPsDbmonInstallAtomJob", lambda *args, **kwargs: {"atom": "dbmon"})
    monkeypatch.setattr(mod, "RedisMakeSyncAtomJob", lambda *args, **kwargs: {"atom": "sync"})
    monkeypatch.setattr(
        mod,
        "GetFileList",
        lambda *args, **kwargs: SimpleNamespace(redis_cluster_version_update=lambda version: []),
    )
    monkeypatch.setattr(mod, "get_major_version_by_version_name", lambda version: TARGET_MAJOR_VERSION)
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: meta_by_id[cluster_id])
    monkeypatch.setattr(
        mod,
        "get_cluster_info_by_ip",
        lambda ip: {"ports": host_ports.get(ip, [30000, 30001])},
    )
    monkeypatch.setattr(mod, "get_twemproxy_cluster_server_shards", lambda *args, **kwargs: {})
    monkeypatch.setattr(mod, "get_cache_backup_mode", lambda *args, **kwargs: "normal")
    monkeypatch.setattr(mod.nosqlcomm.other, "get_cluster_proxies", lambda *args, **kwargs: ["2.2.2.2:50000"])


@pytest.mark.parametrize(
    ("info_item", "expected"),
    [
        ({"cluster_id": 1}, [1]),
        ({"cluster_ids": [1, 2], "cluster_id": 3}, [1, 2]),
    ],
)
def test_get_cluster_ids_from_info_item_accepts_single_and_multi_cluster_inputs(info_item, expected):
    assert RedisClusterVersionUpdateOnline.get_cluster_ids_from_info_item(info_item) == expected


def test_index_info_item_rejects_unknown_node_type():
    flow = _new_flow()

    with pytest.raises(Exception, match="未知的结点类型"):
        flow._index_info_item(_info_item(node_type="Unknown"))


def test_index_info_item_rejects_empty_target_versions():
    flow = _new_flow()

    with pytest.raises(Exception, match="目标版本为空"):
        flow._index_info_item(_info_item(target_versions=[]))


def test_index_info_item_rejects_multiple_versions_for_redis_instance_backend():
    flow = _new_flow()
    flow._cluster_objs[1] = _FakeCluster(cluster_type=ClusterType.TendisRedisInstance)

    with pytest.raises(Exception, match="多个 version"):
        flow._index_info_item(
            _info_item(
                target_versions=[
                    {"ip": "1.1.1.1", "version": TARGET_VERSION},
                    {"ip": "1.1.1.2", "version": "redis-7.0.0"},
                ]
            )
        )


def test_validate_proxy_buckets_rejects_unsupported_target_version(monkeypatch):
    flow = _new_flow()
    flow._cluster_objs[1] = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    flow.cluster_versions_ips["Proxy"][1]["bad-version"] = {"2.2.2.2"}
    monkeypatch.setattr(mod, "get_proxy_version_names_by_cluster_type", lambda *args, **kwargs: [TARGET_VERSION])

    with pytest.raises(Exception, match="目标版本 bad-version 不合法"):
        flow._validate_proxy_buckets()


def test_validate_proxy_buckets_rejects_noop_upgrade(monkeypatch):
    flow = _new_flow()
    flow._cluster_objs[1] = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    flow.cluster_versions_ips["Proxy"][1][TARGET_VERSION] = {"2.2.2.2", "2.2.2.3"}
    monkeypatch.setattr(mod, "get_proxy_version_names_by_cluster_type", lambda *args, **kwargs: [TARGET_VERSION])
    monkeypatch.setattr(mod, "get_proxy_version_by_ip", lambda *args, **kwargs: TARGET_VERSION)

    with pytest.raises(Exception, match="所有proxy当前版本等于目标版本"):
        flow._validate_proxy_buckets()


def test_validate_backend_buckets_rejects_multiple_target_versions():
    flow = _new_flow()
    flow._cluster_objs[1] = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    flow.cluster_versions_ips["Backend"][1][TARGET_VERSION] = {"1.1.1.2"}
    flow.cluster_versions_ips["Backend"][1]["redis-7.0.0"] = {"1.1.1.1"}

    with pytest.raises(Exception, match="不允许在同一单据中升级到多个目标版本"):
        flow._validate_backend_buckets()


def test_validate_backend_target_pair_rejects_unsupported_target_version():
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)

    with pytest.raises(Exception, match="目标版本 bad-version 不合法"):
        flow._validate_backend_target_pair(cluster, [TARGET_VERSION], "bad-version", {"1.1.1.2"})


def test_validate_backend_target_pair_rejects_downgrade(monkeypatch):
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: "redis-7.0.0")
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: _cluster_meta(cluster.cluster_type))

    with pytest.raises(Exception, match="不支持降级"):
        flow._validate_backend_target_pair(cluster, [TARGET_VERSION], TARGET_VERSION, {"1.1.1.2"})


def test_validate_backend_target_pair_rejects_unknown_ip(monkeypatch):
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: CURRENT_VERSION)
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: _cluster_meta(cluster.cluster_type))

    with pytest.raises(Exception, match="既不是master也不是slave"):
        flow._validate_backend_target_pair(cluster, [TARGET_VERSION], TARGET_VERSION, {UNKNOWN_CLUSTER_IP})


def test_validate_backend_target_pair_rejects_master_without_paired_slave(monkeypatch):
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: CURRENT_VERSION)
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: _cluster_meta(cluster.cluster_type))

    with pytest.raises(Exception, match="必须同时将对应 Slave"):
        flow._validate_backend_target_pair(cluster, [TARGET_VERSION], TARGET_VERSION, {"1.1.1.1"})


def test_validate_backend_target_pair_accepts_master_and_slave(monkeypatch):
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisPredixyRedisCluster)
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: CURRENT_VERSION)
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: _cluster_meta(cluster.cluster_type))

    flow._validate_backend_target_pair(cluster, [TARGET_VERSION], TARGET_VERSION, {"1.1.1.1", "1.1.1.2"})


def test_register_instance_info_item_rejects_unknown_pair_ip():
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisRedisInstance)

    with pytest.raises(Exception, match="不属于该集群的主从对"):
        flow._register_instance_info_item(cluster, TARGET_VERSION, {"1.1.1.2", UNKNOWN_CLUSTER_IP})


def test_register_instance_info_item_rejects_missing_slave_ip():
    flow = _new_flow()
    cluster = _FakeCluster(cluster_type=ClusterType.TendisRedisInstance)

    with pytest.raises(Exception, match="必须包含 slave_ip"):
        flow._register_instance_info_item(cluster, TARGET_VERSION, {"1.1.1.1"})


def test_validate_instance_pair_buckets_rejects_one_ip_with_multiple_partners():
    flow = _new_flow()
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": [1],
            "upgrade_master_flags": {False},
        }
    }
    flow.instance_ip_index = {
        "1.1.1.1": {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": {1},
            "pair_partners": {"1.1.1.2", "1.1.1.3"},
            "as_master_cluster_ids": {1},
            "as_slave_cluster_ids": set(),
        }
    }

    with pytest.raises(Exception, match="存在多种主从配对"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_rejects_inconsistent_ip_target_versions():
    flow = _new_flow()
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": [1],
            "upgrade_master_flags": {False},
        }
    }
    flow.instance_ip_index = {
        "1.1.1.1": {
            "target_versions": {TARGET_VERSION, "redis-7.0.0"},
            "cluster_ids": {1},
            "pair_partners": {"1.1.1.2"},
            "as_master_cluster_ids": {1},
            "as_slave_cluster_ids": set(),
        }
    }

    with pytest.raises(Exception, match="目标版本不一致"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_rejects_missing_sibling_clusters(monkeypatch):
    flow = _new_flow()
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": [1],
            "upgrade_master_flags": {False},
        }
    }
    flow.instance_ip_index = {
        "1.1.1.1": {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": {1},
            "pair_partners": {"1.1.1.2"},
            "as_master_cluster_ids": {1},
            "as_slave_cluster_ids": set(),
        },
        "1.1.1.2": {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": {1},
            "pair_partners": {"1.1.1.1"},
            "as_master_cluster_ids": set(),
            "as_slave_cluster_ids": {1},
        },
    }
    flow.instance_cluster_meta[1] = {"cluster": _FakeCluster(cluster_type=ClusterType.TendisRedisInstance)}
    monkeypatch.setattr(
        mod.StorageInstance,
        "objects",
        _FakeStorageObjects(
            {
                ("1.1.1.1", InstanceRole.REDIS_MASTER.value): {1, 2},
                ("1.1.1.2", InstanceRole.REDIS_SLAVE.value): {1},
            }
        ),
    )

    with pytest.raises(Exception, match="未加入本次升级"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_rejects_inconsistent_upgrade_scope(monkeypatch):
    flow = _new_flow()
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": [1, 2],
            "upgrade_master_flags": {True, False},
        }
    }
    flow.instance_ip_index = _valid_instance_ip_index({1, 2})
    monkeypatch.setattr(mod.StorageInstance, "objects", _instance_storage_objects({1, 2}))

    with pytest.raises(Exception, match="升级范围不一致"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_rejects_unsupported_target_version(monkeypatch):
    flow = _valid_instance_pair_flow(target_version="bad-version")
    monkeypatch.setattr(mod.StorageInstance, "objects", _instance_storage_objects({1}))
    monkeypatch.setattr(mod, "get_storage_version_names_by_cluster_type", lambda *args, **kwargs: [TARGET_VERSION])

    with pytest.raises(Exception, match="目标版本 bad-version 不合法"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_rejects_downgrade(monkeypatch):
    flow = _valid_instance_pair_flow()
    monkeypatch.setattr(mod.StorageInstance, "objects", _instance_storage_objects({1}))
    monkeypatch.setattr(mod, "get_storage_version_names_by_cluster_type", lambda *args, **kwargs: [TARGET_VERSION])
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: "redis-7.0.0")

    with pytest.raises(Exception, match="不支持降级"):
        flow._validate_instance_pair_buckets()


def test_validate_instance_pair_buckets_finalizes_valid_bucket(monkeypatch):
    flow = _valid_instance_pair_flow(upgrade_master=True)
    monkeypatch.setattr(mod.StorageInstance, "objects", _instance_storage_objects({1}))
    monkeypatch.setattr(mod, "get_storage_version_names_by_cluster_type", lambda *args, **kwargs: [TARGET_VERSION])
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: CURRENT_VERSION)

    flow._validate_instance_pair_buckets()

    bucket = flow.instance_pair_buckets[("1.1.1.1", "1.1.1.2")]
    assert bucket["target_version"] == TARGET_VERSION
    assert bucket["upgrade_master"] is True
    assert "target_versions" not in bucket
    assert "upgrade_master_flags" not in bucket


def _valid_instance_ip_index(cluster_ids):
    return {
        "1.1.1.1": {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": set(cluster_ids),
            "pair_partners": {"1.1.1.2"},
            "as_master_cluster_ids": set(cluster_ids),
            "as_slave_cluster_ids": set(),
        },
        "1.1.1.2": {
            "target_versions": {TARGET_VERSION},
            "cluster_ids": set(cluster_ids),
            "pair_partners": {"1.1.1.1"},
            "as_master_cluster_ids": set(),
            "as_slave_cluster_ids": set(cluster_ids),
        },
    }


def _instance_storage_objects(cluster_ids):
    return _FakeStorageObjects(
        {
            ("1.1.1.1", InstanceRole.REDIS_MASTER.value): set(cluster_ids),
            ("1.1.1.2", InstanceRole.REDIS_SLAVE.value): set(cluster_ids),
        }
    )


def _valid_instance_pair_flow(target_version=TARGET_VERSION, upgrade_master=False):
    flow = _new_flow()
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "target_versions": {target_version},
            "cluster_ids": [1],
            "upgrade_master_flags": {upgrade_master},
        }
    }
    flow.instance_ip_index = _valid_instance_ip_index({1})
    flow.instance_cluster_meta[1] = {"cluster": _FakeCluster(cluster_type=ClusterType.TendisRedisInstance)}
    return flow


@pytest.mark.parametrize(
    "cluster_type",
    [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyTendisplusIns,
    ],
)
def test_proxy_upgrade_flow_builds_for_proxy_supported_cluster_types(monkeypatch, cluster_type):
    meta_by_id = {1: _cluster_meta(cluster_type)}
    _install_recorder_build_stubs(monkeypatch, meta_by_id)
    flow = _construct_flow_without_precheck(monkeypatch)
    flow.cluster_versions_ips["Proxy"][1][TARGET_VERSION] = {"2.2.2.2", "2.2.2.3"}

    flow.version_update_flow()

    assert _RecorderBuilder.created[0].ran is True
    assert _RecorderBuilder.created[0].parallel_sub_pipelines
    assert any("update_proxy" in name for name in _flatten_act_names())


@pytest.mark.parametrize(
    "cluster_type",
    [
        ClusterType.RedisCluster,
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.TendisPredixyTendisplusCluster,
    ],
)
def test_backend_flow_builds_redis_cluster_protocol_switch_branch(monkeypatch, cluster_type):
    meta_by_id = {1: _cluster_meta(cluster_type)}
    _install_recorder_build_stubs(monkeypatch, meta_by_id)
    flow = _construct_flow_without_precheck(monkeypatch)
    flow.cluster_versions_ips["Backend"][1][TARGET_VERSION] = {"1.1.1.1", "1.1.1.2"}

    flow.version_update_flow()

    names = _flatten_act_names()
    assert _RecorderBuilder.created[0].ran is True
    assert any("cluster failover" in name for name in names)
    assert any("Backend数据更新收尾" == builder.sub_name for builder in _RecorderBuilder.created)


@pytest.mark.parametrize(
    "cluster_type",
    [
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyTendisplusIns,
    ],
)
def test_backend_flow_builds_twemproxy_switch_branch(monkeypatch, cluster_type):
    meta_by_id = {1: _cluster_meta(cluster_type)}
    _install_recorder_build_stubs(monkeypatch, meta_by_id)
    flow = _construct_flow_without_precheck(monkeypatch)
    flow.cluster_versions_ips["Backend"][1][TARGET_VERSION] = {"1.1.1.1", "1.1.1.2"}

    flow.version_update_flow()

    names = _flatten_act_names()
    assert _RecorderBuilder.created[0].ran is True
    assert any("主从切换" in name for name in names)
    assert any("删除slaveof配置" in name for name in names)
    assert any("Backend数据更新收尾" == builder.sub_name for builder in _RecorderBuilder.created)


@pytest.mark.parametrize(
    "cluster_type",
    [
        ClusterType.TendisRedisCluster,
        ClusterType.TendisTendisSSDInstance,
        ClusterType.TendisTendisplusInsance,
        ClusterType.TendisTendisplusCluster,
    ],
)
def test_backend_flow_builds_slave_only_for_remaining_storage_supported_types(monkeypatch, cluster_type):
    meta_by_id = {1: _cluster_meta(cluster_type)}
    _install_recorder_build_stubs(monkeypatch, meta_by_id)
    flow = _construct_flow_without_precheck(monkeypatch)
    flow.cluster_versions_ips["Backend"][1][TARGET_VERSION] = {"1.1.1.2"}

    flow.version_update_flow()

    names = _flatten_act_names()
    assert _RecorderBuilder.created[0].ran is True
    assert any("old_slave:1.1.1.2 版本升级" == name for name in names)
    assert not any("cluster failover" in name or "主从切换" in name for name in names)


@pytest.mark.parametrize("upgrade_master", [False, True])
def test_redis_instance_pair_flow_builds_slave_only_and_master_upgrade_variants(monkeypatch, upgrade_master):
    meta_by_id = {1: _cluster_meta(ClusterType.TendisRedisInstance)}
    _install_recorder_build_stubs(
        monkeypatch,
        meta_by_id,
        host_ports={"1.1.1.1": [30000, 30001], "1.1.1.2": [30000, 30001]},
    )
    flow = _construct_flow_without_precheck(monkeypatch)
    flow.instance_pair_buckets = {
        ("1.1.1.1", "1.1.1.2"): {
            "cluster_ids": [1],
            "target_version": TARGET_VERSION,
            "upgrade_master": upgrade_master,
        }
    }

    flow.version_update_flow()

    names = _flatten_act_names()
    assert _RecorderBuilder.created[0].ran is True
    assert any("old_slave:1.1.1.2 版本升级至 Redis-6" == name for name in names)
    if upgrade_master:
        assert any("域名指向修改" in name for name in names)
        assert any("new_slave(1.1.1.1)-版本升级至 Redis-6" == name for name in names)
    else:
        assert not any("域名指向修改" in name for name in names)


def test_real_builder_smoke_validates_representative_proxy_and_backend_pipeline(monkeypatch):
    from backend.flow.engine.bamboo.scene.common import builder as common_builder
    from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
    from backend.tests.mock_data.components.engine_run_pipeline import EngineApiMock

    meta_by_id = {1: _cluster_meta(ClusterType.TendisPredixyRedisCluster)}

    def empty_sub_process(name):
        sub_builder = SubBuilder(root_id="root-1", data=_ticket_data())
        sub_builder.add_act(
            act_name="{} noop".format(name),
            act_component_code=mod.EmptyNodeComponent.code,
            kwargs={},
        )
        return sub_builder.build_sub_process(name)

    monkeypatch.setattr(RedisClusterVersionUpdateOnline, "precheck", lambda self: None)
    monkeypatch.setattr(mod, "ClusterProxysUpgradeAtomJob", lambda *args, **kwargs: empty_sub_process("proxy-upgrade"))
    monkeypatch.setattr(mod, "ClusterIPsDbmonInstallAtomJob", lambda *args, **kwargs: empty_sub_process("dbmon"))
    monkeypatch.setattr(
        mod,
        "GetFileList",
        lambda *args, **kwargs: SimpleNamespace(redis_cluster_version_update=lambda version: []),
    )
    monkeypatch.setattr(mod, "get_major_version_by_version_name", lambda version: TARGET_MAJOR_VERSION)
    monkeypatch.setattr(mod, "get_cluster_info_by_cluster_id", lambda cluster_id: meta_by_id[cluster_id])
    monkeypatch.setattr(mod, "get_redis_version_by_ip", lambda *args, **kwargs: CURRENT_VERSION)
    monkeypatch.setattr(mod, "get_proxy_version_by_ip", lambda *args, **kwargs: "predixy-1.3.0")
    monkeypatch.setattr(common_builder.FlowTree.objects, "create", lambda **kwargs: None)
    monkeypatch.setattr(common_builder.api, "run_pipeline", EngineApiMock.run_pipeline)
    EngineApiMock.was_called = False
    EngineApiMock.last_result = None
    EngineApiMock.last_exception = None

    flow = RedisClusterVersionUpdateOnline(root_id="root-1", data=_ticket_data())
    flow.cluster_versions_ips["Proxy"][1]["predixy-1.4.0"] = {"2.2.2.2"}
    flow.cluster_versions_ips["Backend"][1][TARGET_VERSION] = {"1.1.1.2"}

    flow.version_update_flow()

    assert EngineApiMock.was_called is True
    assert EngineApiMock.last_result.result is True, EngineApiMock.last_result.message
