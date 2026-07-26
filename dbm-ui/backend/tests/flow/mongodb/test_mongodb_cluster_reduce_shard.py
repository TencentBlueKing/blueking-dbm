# -*- coding: utf-8 -*-
"""MongoDB 分片集群减少分片数：serializer / calculate / pipeline 顺序测试."""

from types import SimpleNamespace

import pytest

from backend.db_meta.enums import InstanceRole
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.mongodb.mongodb_cluster_reduce_shard import MongoDBClusterReduceShardFlow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.cluster_reduce_shard_meta import (
    ExecReduceShardMetaOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.calculate_cluster import (
    _validate_co_located_shard_group,
    calculate_cluster_reduce_shard,
)
from backend.flow.utils.mongodb.mongodb_repo import MongoNode, ReplicaSet, ShardedCluster


def _member(ip, port, role=InstanceRole.MONGO_M1.value):
    return MongoNode(ip, port, role, 0, "mongodb")


def _shard(set_name, members):
    return ReplicaSet(MongoDBClusterRole.ShardSvr.value, set_name=set_name, members=members)


def _fake_cluster(shards, mongos_ip="127.0.0.10"):
    mongos = MongoNode(mongos_ip, 27017, MongoDBClusterRole.Mongos.value, 0, "mongos")
    config = ReplicaSet(
        MongoDBClusterRole.ConfigSvr.value,
        set_name="demo-config",
        members=[_member("127.0.0.20", 27019)],
    )
    return ShardedCluster(
        bk_cloud_id=0,
        cluster_id=1001,
        name="demo",
        major_version="5.0.0",
        bk_biz_id=3,
        immute_domain="demo.mongodb.db",
        shards=shards,
        mongos=[mongos],
        configsvr=config,
    )


def _base_payload(**overrides):
    payload = {
        "uid": "mongo-reduce-shard-3-20260724-001",
        "ticket_id": "1111",
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "ticket_type": "MongoDBReduceShardFlow",
        "created_by": "tester",
        "infos": [{"cluster_id": 1001, "shard_names": ["demo-s3"], "bk_cloud_id": 0}],
    }
    payload.update(overrides)
    return payload


class TestMongoDBClusterReduceShardSerializer:
    def test_empty_uid_rejected(self):
        s = MongoDBClusterReduceShardFlow.Serializer(data=_base_payload(uid=""))
        assert s.is_valid() is False
        assert "uid" in s.errors

    def test_empty_shard_names_rejected(self):
        s = MongoDBClusterReduceShardFlow.Serializer(
            data=_base_payload(infos=[{"cluster_id": 1001, "shard_names": []}])
        )
        assert s.is_valid() is False

    def test_missing_infos_rejected(self):
        data = _base_payload()
        data.pop("infos")
        s = MongoDBClusterReduceShardFlow.Serializer(data=data)
        assert s.is_valid() is False


class TestCalculateClusterReduceShard:
    def test_would_remove_all_shards(self, monkeypatch):
        shards = [
            _shard("demo-s1", [_member("127.0.0.1", 27001), _member("127.0.0.2", 27001)]),
        ]
        cluster = _fake_cluster(shards)
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        with pytest.raises(ValueError, match="would remove all shards"):
            calculate_cluster_reduce_shard(_base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s1"]}]))

    def test_co_located_incomplete_fails(self, monkeypatch):
        # 同机多分片：127.0.0.1 上有 s1 和 s2
        shards = [
            _shard(
                "demo-s1",
                [
                    _member("127.0.0.1", 27001, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.2", 27001, InstanceRole.MONGO_M2.value),
                ],
            ),
            _shard(
                "demo-s2",
                [
                    _member("127.0.0.1", 27002, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.2", 27002, InstanceRole.MONGO_M2.value),
                ],
            ),
            _shard(
                "demo-s3",
                [
                    _member("127.0.0.3", 27001, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.4", 27001, InstanceRole.MONGO_M2.value),
                ],
            ),
        ]
        cluster = _fake_cluster(shards)
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        with pytest.raises(ValueError, match="co-located shard group incomplete"):
            calculate_cluster_reduce_shard(_base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s1"]}]))

    def test_co_located_complete_ok(self, monkeypatch):
        shards = [
            _shard(
                "demo-s1",
                [
                    _member("127.0.0.1", 27001, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.2", 27001, InstanceRole.MONGO_M2.value),
                ],
            ),
            _shard(
                "demo-s2",
                [
                    _member("127.0.0.1", 27002, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.2", 27002, InstanceRole.MONGO_M2.value),
                ],
            ),
            _shard(
                "demo-s3",
                [
                    _member("127.0.0.3", 27001, InstanceRole.MONGO_M1.value),
                    _member("127.0.0.4", 27001, InstanceRole.MONGO_M2.value),
                ],
            ),
        ]
        cluster = _fake_cluster(shards)
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        result = calculate_cluster_reduce_shard(
            _base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s1", "demo-s2"]}])
        )
        info = result["cluster_reduce_shard_info"][0]
        assert set(info["reduce_shards"]) == {"demo-s1", "demo-s2"}
        assert len(info["old_instances"]) == 4
        assert info["cluster_name"] == "demo"

    def test_validate_co_located_helper_direct(self):
        shards = [
            _shard("s1", [_member("127.0.0.1", 1)]),
            _shard("s2", [_member("127.0.0.1", 2)]),
            _shard("s3", [_member("127.0.0.3", 1)]),
        ]
        with pytest.raises(ValueError, match="co-located"):
            _validate_co_located_shard_group(shards, {"s1"})
        _validate_co_located_shard_group(shards, {"s1", "s2"})


class TestClusterReduceShardPipelineOrder:
    def test_pipeline_contains_required_stages_in_order(self, monkeypatch):
        # sub_task/__init__ 会把同名函数绑定到包属性，遮盖子模块；必须用 importlib 取真实模块再 patch
        import importlib

        mod = importlib.import_module("backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_reduce_shard")

        recorded = []

        class FakeSubBuilder:
            def __init__(self, *args, **kwargs):
                pass

            def add_act(self, act_name=None, act_component_code=None, kwargs=None):
                recorded.append(("act", act_name, act_component_code))

            def add_sub_pipeline(self, sub_flow=None):
                recorded.append(("sub", "multi_instance_deinstall", None))

            def build_sub_process(self, sub_name=None):
                return SimpleNamespace(name=sub_name, recorded=list(recorded))

        class FakeKwargs:
            manager_users = ["dba"]

            def __init__(self):
                self.payload = {}

            def get_send_media_kwargs(self, media_type="actuator"):
                return {"media": media_type}

            def get_create_dir_kwargs(self):
                return {"dir": True}

            def get_password_from_db(self, info):
                return {"passwords": {"dba": "pwd"}}

            def get_balancer_kwargs(self, open=True):
                return {"balancer": open}

            def get_remove_shard_from_cluster_kwargs(self):
                return {"remove": True}

            def get_reduce_shard_delete_pwd_kwargs(self, instances):
                return {"pwd": len(instances)}

            def get_reduce_shard_to_meta_kwargs(self, info):
                return {"meta": info["cluster_id"]}

        monkeypatch.setattr(mod, "SubBuilder", FakeSubBuilder)
        monkeypatch.setattr(
            mod,
            "multi_instance_deinstall",
            lambda **kwargs: SimpleNamespace(name="deinstall"),
        )

        reduce_info = {
            "cluster_id": 1001,
            "cluster_name": "demo",
            "bk_cloud_id": 0,
            "mongos": {"port": 27017, "nodes": [{"ip": "127.0.0.10", "port": 27017, "bk_cloud_id": 0}]},
            "reduce_shards": ["demo-s1"],
            "storages": [{"shard": "demo-s1", "nodes": [{"ip": "127.0.0.1", "port": 27001}]}],
            "hosts": [{"ip": "127.0.0.1", "bk_cloud_id": 0}, {"ip": "127.0.0.10", "bk_cloud_id": 0}],
            "old_hosts": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "old_instances": [{"ip": "127.0.0.1", "port": 27001, "bk_cloud_id": 0, "set_id": "demo-s1"}],
        }

        mod.cluster_reduce_shard(
            root_id="root",
            ticket_data={"uid": "mongo-reduce-shard-3-20260724-001"},
            sub_kwargs=FakeKwargs(),
            reduce_shard_info=reduce_info,
        )

        codes = [item[2] for item in recorded if item[0] == "act"]
        # removeShard (exec actuator) → pause → deinstall sub → meta
        remove_idx = next(i for i, item in enumerate(recorded) if item[0] == "act" and "移除shards" in (item[1] or ""))
        pause_idx = next(i for i, item in enumerate(recorded) if item[2] == PauseComponent.code)
        deinstall_idx = next(i for i, item in enumerate(recorded) if item[0] == "sub")
        meta_idx = next(i for i, item in enumerate(recorded) if item[2] == ExecReduceShardMetaOperationComponent.code)
        assert remove_idx < pause_idx < deinstall_idx < meta_idx
        assert ExecuteDBActuatorJobComponent.code in codes
