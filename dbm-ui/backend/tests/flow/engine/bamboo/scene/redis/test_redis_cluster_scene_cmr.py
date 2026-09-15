# -*- coding: utf-8 -*-
"""
整机替换场景(redis_cluster_scene_cmr)单测:
验证 rediscluster/tendisplus 等集群协议集群在替换 slave/master 后,
追加 forget 旧实例的步骤
"""
from types import SimpleNamespace

import pytest

import backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_cmr as cmr_mod
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_cmr import RedisClusterCMRSceneFlow
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs


class _RecorderBuilder:
    """记录 act / sub_pipeline 的伪 Builder"""

    created = []

    def __init__(self, root_id=None, data=None):
        self.acts = []
        self.sub_pipelines = []
        self.parallel_sub_pipelines = []
        self.sub_name = None
        _RecorderBuilder.created.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        self.acts.append({"act_name": act_name, "act_component_code": act_component_code, "kwargs": kwargs, **extra})

    def add_sub_pipeline(self, sub_builder=None, **kwargs):
        self.sub_pipelines.append(sub_builder if sub_builder is not None else kwargs.get("sub_flow"))

    def add_parallel_sub_pipeline(self, sub_flow_list=None, **kwargs):
        self.parallel_sub_pipelines.append(list(sub_flow_list or kwargs.get("sub_flow_list") or []))

    def build_sub_process(self, sub_name, **kwargs):
        self.sub_name = sub_name
        return self


def _fake_replace_job(root_id, ticket_data, sub_kwargs, replace_info):
    return _RecorderBuilder().build_sub_process(sub_name="fake-replace-job")


class _FakeProxyInstanceQuery:
    def all(self):
        return [SimpleNamespace(machine=SimpleNamespace(ip="3.3.3.3"))]


class _FakeCluster:
    proxyinstance_set = _FakeProxyInstanceQuery()


class _FakeClusterObjects:
    @staticmethod
    def get(**kwargs):
        return _FakeCluster()


def _ticket_data():
    return {
        "uid": "202609150001",
        "bk_biz_id": 100,
        "created_by": "tester",
        "ticket_type": "REDIS_CLUSTER_CUTOFF",
        "sync_type": "ms",
        "infos": [],
    }


def _make_flow():
    flow = object.__new__(RedisClusterCMRSceneFlow)
    flow.root_id = "root-cmr-1"
    flow.data = _ticket_data()
    flow.cluster_cache = {}
    return flow


def _make_act_kwargs(cluster_type):
    kwargs = ActKwargs()
    kwargs.set_trans_data_dataclass = "CommonContext"
    kwargs.is_update_trans_data = True
    kwargs.bk_cloud_id = 0
    kwargs.cluster = {
        "operate": "REDIS-整机替换",
        "bk_biz_id": 100,
        "bk_cloud_id": 0,
        "cluster_id": 1,
        "cluster_name": "test",
        "cluster_type": cluster_type,
        "immute_domain": "cluster.test.db",
        "major_version": "Redis-5",
        "db_version": "Redis-5",
        "master_ports": {"1.1.1.1": [30000, 30001]},
        "slave_ports": {"2.2.2.2": [30000, 30001]},
        "ins_pair_map": {"1.1.1.1:30000": "2.2.2.2:30000", "1.1.1.1:30001": "2.2.2.2:30001"},
        "slave_ins_map": {"2.2.2.2:30000": "1.1.1.1:30000", "2.2.2.2:30001": "1.1.1.1:30001"},
        "master_slave_map": {"1.1.1.1": "2.2.2.2"},
        "slave_master_map": {"2.2.2.2": "1.1.1.1"},
        "proxy_port": 50000,
        "proxy_ips": ["3.3.3.3"],
        "backend_servers": [],
    }
    return kwargs


def _find_forget_act(builder):
    for act in builder.acts:
        if (
            act["act_component_code"] == ExecuteDBActuatorScriptComponent.code
            and act["kwargs"].get("get_redis_payload_func") == RedisActPayload.redis_cluster_forget_4_scene.__name__
        ):
            return act
    return None


@pytest.fixture
def patch_cmr_scene(monkeypatch):
    _RecorderBuilder.created = []
    monkeypatch.setattr(cmr_mod, "SubBuilder", _RecorderBuilder)
    monkeypatch.setattr(cmr_mod, "RedisClusterSlaveReplaceJob", _fake_replace_job)
    monkeypatch.setattr(cmr_mod, "RedisClusterMasterReplaceJob", _fake_replace_job)
    monkeypatch.setattr(cmr_mod, "ClusterPredixyConfigServersRewriteAtomJob", lambda *args, **kwargs: None)
    monkeypatch.setattr(cmr_mod, "Cluster", SimpleNamespace(objects=_FakeClusterObjects()))


class TestRedisClusterCMRForgetOldInstances(object):
    def test_rediscluster_slave_replace_forget_old_instances(self, patch_cmr_scene):
        """rediscluster集群替换slave后, 需要forget旧slave机器上的全部实例"""
        flow = _make_flow()
        act_kwargs = _make_act_kwargs(ClusterType.TendisPredixyRedisCluster.value)
        replacement = {
            "cluster_ids": [1],
            "redis_slave": [{"ip": "2.2.2.2", "spec_id": 1, "target": {"ip": "4.4.4.4", "spec": {}}}],
        }

        sub = flow.generate_cluster_replacement(flow.data, act_kwargs, replacement)

        act = _find_forget_act(sub)
        assert act is not None, "rediscluster替换slave后应存在forget旧实例步骤"
        assert act["kwargs"]["cluster"]["forget_instances"] == [
            {"ip": "2.2.2.2", "port": 30000},
            {"ip": "2.2.2.2", "port": 30001},
        ]
        # actuator 在新替换的节点上执行
        assert act["kwargs"]["exec_ip"] == "4.4.4.4"
        assert act["kwargs"]["cluster"]["immute_domain"] == "cluster.test.db"
        assert act["kwargs"]["cluster"]["cluster_type"] == ClusterType.TendisPredixyRedisCluster.value

    def test_tendisplus_master_replace_forget_old_instances(self, patch_cmr_scene):
        """tendisplus集群替换master后, 旧master与配对旧slave的实例都需要forget, 且按ip:port去重"""
        flow = _make_flow()
        act_kwargs = _make_act_kwargs(ClusterType.TendisPredixyTendisplusCluster.value)
        replacement = {
            "cluster_ids": [1],
            # 2.2.2.2 既是被替换的slave, 也是 1.1.1.1 配对的旧slave, 不应重复forget
            "redis_slave": [{"ip": "2.2.2.2", "spec_id": 1, "target": {"ip": "4.4.4.4", "spec": {}}}],
            "redis_master": [
                {
                    "ip": "1.1.1.1",
                    "spec_id": 2,
                    "target": {"master": {"ip": "5.5.5.5", "spec": {}}, "slave": {"ip": "6.6.6.6", "spec": {}}},
                }
            ],
        }

        sub = flow.generate_cluster_replacement(flow.data, act_kwargs, replacement)

        act = _find_forget_act(sub)
        assert act is not None, "tendisplus替换master后应存在forget旧实例步骤"
        assert act["kwargs"]["cluster"]["forget_instances"] == [
            {"ip": "2.2.2.2", "port": 30000},
            {"ip": "2.2.2.2", "port": 30001},
            {"ip": "1.1.1.1", "port": 30000},
            {"ip": "1.1.1.1", "port": 30001},
        ]
        # master替换场景优先在新master节点上执行
        assert act["kwargs"]["exec_ip"] == "5.5.5.5"

    def test_twemproxy_cluster_no_forget(self, patch_cmr_scene):
        """twemproxy类型(tendiscache)不适用cluster forget, 不应有该步骤"""
        flow = _make_flow()
        act_kwargs = _make_act_kwargs(ClusterType.TendisTwemproxyRedisInstance.value)
        replacement = {
            "cluster_ids": [1],
            "redis_slave": [{"ip": "2.2.2.2", "spec_id": 1, "target": {"ip": "4.4.4.4", "spec": {}}}],
        }

        sub = flow.generate_cluster_replacement(flow.data, act_kwargs, replacement)

        assert _find_forget_act(sub) is None

    def test_proxy_only_replace_no_forget(self, patch_cmr_scene):
        """仅替换proxy不涉及存储节点时, 不应有forget步骤"""
        flow = _make_flow()
        act_kwargs = _make_act_kwargs(ClusterType.TendisPredixyRedisCluster.value)
        replacement = {
            "cluster_ids": [1],
            "proxy": [{"ip": "3.3.3.3", "spec_id": 3, "target": {"ip": "7.7.7.7", "spec": {}}}],
        }

        sub = flow.generate_cluster_replacement(flow.data, act_kwargs, replacement)

        assert _find_forget_act(sub) is None
