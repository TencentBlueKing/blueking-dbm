# -*- coding: utf-8 -*-
"""MongoDB 分片集群减少分片数：serializer / calculate / pipeline 顺序测试."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import InstanceRole
from backend.flow.consts import MongoDBClusterRole, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.mongodb.mongodb_cluster_reduce_shard import MongoDBClusterReduceShardFlow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.cluster_reduce_shard_meta import (
    ExecReduceShardMetaOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.calculate_cluster import (
    _validate_remaining_shard_deployment_balanced,
    calculate_cluster_reduce_shard,
)
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
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


def _patch_db_version(monkeypatch, version="5.0.0"):
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.calculate_cluster.Cluster.objects.get",
        lambda **kwargs: SimpleNamespace(id=kwargs.get("pk", 1001), major_version=version),
    )
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.calculate_cluster.resolve_mongodb_flow_db_version",
        lambda cluster: version,
    )


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

    def test_default_mode_with_shard_names_ok(self):
        s = MongoDBClusterReduceShardFlow.Serializer(data=_base_payload())
        assert s.is_valid(), s.errors
        assert s.validated_data["infos"][0]["reduce_mode"] == "by_shard_names"
        assert s.validated_data["infos"][0]["shard_names"] == ["demo-s3"]
        assert "reduce_shards_num" not in s.validated_data["infos"][0]

    def test_by_count_mode_ok(self):
        s = MongoDBClusterReduceShardFlow.Serializer(
            data=_base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_count", "reduce_shards_num": 2}])
        )
        assert s.is_valid(), s.errors
        info = s.validated_data["infos"][0]
        assert info["reduce_mode"] == "by_count"
        assert info["reduce_shards_num"] == 2
        assert "shard_names" not in info

    def test_by_count_missing_num_rejected(self):
        s = MongoDBClusterReduceShardFlow.Serializer(
            data=_base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_count"}])
        )
        assert s.is_valid() is False

    def test_by_shard_names_missing_names_rejected(self):
        s = MongoDBClusterReduceShardFlow.Serializer(
            data=_base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_shard_names"}])
        )
        assert s.is_valid() is False

    def test_by_shard_names_strips_reduce_shards_num(self):
        s = MongoDBClusterReduceShardFlow.Serializer(
            data=_base_payload(
                infos=[
                    {
                        "cluster_id": 1001,
                        "reduce_mode": "by_shard_names",
                        "shard_names": ["demo-s3"],
                        "reduce_shards_num": 1,
                    }
                ]
            )
        )
        assert s.is_valid(), s.errors
        assert "reduce_shards_num" not in s.validated_data["infos"][0]


def _pair_group(s_a, s_b, ip_a, ip_b):
    """一组机器上部署 2 个分片（单机多片）"""
    return [
        _shard(
            s_a,
            [
                _member(ip_a, 27001, InstanceRole.MONGO_M1.value),
                _member(ip_b, 27001, InstanceRole.MONGO_M2.value),
            ],
        ),
        _shard(
            s_b,
            [
                _member(ip_a, 27002, InstanceRole.MONGO_M1.value),
                _member(ip_b, 27002, InstanceRole.MONGO_M2.value),
            ],
        ),
    ]


def _three_groups_six_shards():
    """3 组机器 × 每组 2 片 = 6 片"""
    shards = []
    shards.extend(_pair_group("demo-s1", "demo-s2", "127.0.0.1", "127.0.0.2"))
    shards.extend(_pair_group("demo-s3", "demo-s4", "127.0.0.3", "127.0.0.4"))
    shards.extend(_pair_group("demo-s5", "demo-s6", "127.0.0.5", "127.0.0.6"))
    return shards


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
        with pytest.raises(ValueError, match="至少保留1个分片"):
            calculate_cluster_reduce_shard(_base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s1"]}]))

    def test_remaining_deployment_unbalanced_by_shard_names(self, monkeypatch):
        # 3 组×2 片；只删 1 片后剩余主机片数混杂（2 与 1）
        cluster = _fake_cluster(_three_groups_six_shards())
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        with pytest.raises(ValueError, match="不均衡"):
            calculate_cluster_reduce_shard(_base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s6"]}]))

    def test_remaining_deployment_balanced_ok_after_full_group_remove(self, monkeypatch):
        # 删一整组 2 片后剩余两组仍均为单机 2 片
        cluster = _fake_cluster(_three_groups_six_shards())
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        _patch_db_version(monkeypatch, "4.4.18")
        result = calculate_cluster_reduce_shard(
            _base_payload(infos=[{"cluster_id": 1001, "shard_names": ["demo-s5", "demo-s6"]}])
        )
        info = result["cluster_reduce_shard_info"][0]
        assert set(info["reduce_shards"]) == {"demo-s5", "demo-s6"}
        assert info["db_version"] == "4.4.18"

    def test_validate_remaining_balanced_helper_direct(self):
        shards = [
            _shard("s1", [_member("127.0.0.1", 1), _member("127.0.0.2", 1)]),
            _shard("s2", [_member("127.0.0.1", 2), _member("127.0.0.2", 2)]),
            _shard("s3", [_member("127.0.0.3", 1), _member("127.0.0.4", 1)]),
        ]
        with pytest.raises(ValueError, match="不均衡"):
            _validate_remaining_shard_deployment_balanced(shards, set())
        _validate_remaining_shard_deployment_balanced(shards, {"s1", "s2"})
        _validate_remaining_shard_deployment_balanced(shards, {"s3"})

    def test_get_shards_sort_does_not_mutate(self):
        shards = [
            _shard("demo-s3", [_member("127.0.0.5", 27001)]),
            _shard("demo-s1", [_member("127.0.0.1", 27001)]),
            _shard("demo-s2", [_member("127.0.0.3", 27001)]),
        ]
        cluster = _fake_cluster(list(shards))
        before = [s.set_name for s in cluster.shards]
        ordered = [s.set_name for s in cluster.get_shards(sort_by_set_name=True)]
        after = [s.set_name for s in cluster.shards]
        assert before == after == ["demo-s3", "demo-s1", "demo-s2"]
        assert ordered == ["demo-s1", "demo-s2", "demo-s3"]

    def test_by_count_picks_highest_numbered_shards(self, monkeypatch):
        # 每机 1 片时缩 2 片：取编号最大的 2 个，剩余仍均衡
        shards = [
            _shard("demo-s1", [_member("127.0.0.1", 27001), _member("127.0.0.2", 27001)]),
            _shard("demo-s2", [_member("127.0.0.3", 27001), _member("127.0.0.4", 27001)]),
            _shard("demo-s3", [_member("127.0.0.5", 27001), _member("127.0.0.6", 27001)]),
        ]
        cluster = _fake_cluster(shards)
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        _patch_db_version(monkeypatch)
        result = calculate_cluster_reduce_shard(
            _base_payload(
                infos=[{"cluster_id": 1001, "reduce_mode": "by_count", "reduce_shards_num": 2, "bk_cloud_id": 0}]
            )
        )
        info = result["cluster_reduce_shard_info"][0]
        assert info["reduce_shards"] == ["demo-s2", "demo-s3"]

    def test_by_count_would_remove_all_fails(self, monkeypatch):
        shards = [
            _shard("demo-s1", [_member("127.0.0.1", 27001), _member("127.0.0.2", 27001)]),
            _shard("demo-s2", [_member("127.0.0.3", 27001), _member("127.0.0.4", 27001)]),
        ]
        cluster = _fake_cluster(shards)
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        with pytest.raises(ValueError, match="至少保留1个分片"):
            calculate_cluster_reduce_shard(
                _base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_count", "reduce_shards_num": 2}])
            )

    @pytest.mark.parametrize("n", [2, 4, 5])
    def test_by_count_six_shards_allowed_counts(self, monkeypatch, n):
        # 3 组×2 片：按编号从大缩 N=2/4/5 时剩余均衡
        cluster = _fake_cluster(_three_groups_six_shards())
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        _patch_db_version(monkeypatch)
        result = calculate_cluster_reduce_shard(
            _base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_count", "reduce_shards_num": n}])
        )
        assert len(result["cluster_reduce_shard_info"][0]["reduce_shards"]) == n

    @pytest.mark.parametrize("n", [1, 3])
    def test_by_count_six_shards_forbidden_counts(self, monkeypatch, n):
        # 3 组×2 片：缩 1/3 会导致剩余主机片数混杂
        cluster = _fake_cluster(_three_groups_six_shards())
        monkeypatch.setattr(
            "backend.flow.utils.mongodb.calculate_cluster.MongoRepository.fetch_one_cluster",
            classmethod(lambda cls, with_domain=False, with_tags=False, **kwargs: cluster),
        )
        with pytest.raises(ValueError, match="不均衡"):
            calculate_cluster_reduce_shard(
                _base_payload(infos=[{"cluster_id": 1001, "reduce_mode": "by_count", "reduce_shards_num": n}])
            )


class TestReduceShardActKwargs:
    def _kwargs(self):
        act = ActKwargs()
        act.file_path = "/tmp"
        act.payload = {
            "nodes": [{"ip": "127.0.0.10", "port": 27017, "bk_cloud_id": 0}],
            "mongos": {"port": 27017, "nodes": [{"ip": "127.0.0.10", "port": 27017, "bk_cloud_id": 0}]},
            "reduce_shards": ["demo-s1"],
            "db_version": "4.4.18",
            "passwords": {MongoDBManagerUser.DbaUser.value: "secret"},
        }
        return act

    def test_open_balancer_skips_wait_when_false(self):
        kwargs = self._kwargs().get_balancer_kwargs(open=True, wait_for_balance=False)
        payload = kwargs["db_act_template"]["payload"]
        assert payload["open"] is True
        assert payload["waitForBalance"] is False

    def test_open_balancer_waits_by_default(self):
        kwargs = self._kwargs().get_balancer_kwargs(open=True)
        assert kwargs["db_act_template"]["payload"]["waitForBalance"] is True

    def test_remove_shard_kwargs_include_db_version(self):
        kwargs = self._kwargs().get_remove_shard_from_cluster_kwargs()
        payload = kwargs["db_act_template"]["payload"]
        assert payload["shards"] == ["demo-s1"]
        assert payload["dbVersion"] == "4.4.18"


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
                recorded.append(("act", act_name, act_component_code, kwargs))

            def add_sub_pipeline(self, sub_flow=None):
                recorded.append(("sub", "multi_instance_deinstall", None, None))

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

            def get_balancer_kwargs(self, open=True, wait_for_balance=True):
                return {"balancer": open, "waitForBalance": wait_for_balance}

            def get_remove_shard_from_cluster_kwargs(self):
                return {"remove": True, "dbVersion": self.payload.get("db_version")}

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
            "db_version": "4.4.18",
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

        open_balancer = next(item for item in recorded if item[0] == "act" and "打开balancer" in (item[1] or ""))
        assert open_balancer[3]["waitForBalance"] is False
        remove_act = recorded[remove_idx]
        assert remove_act[3]["dbVersion"] == "4.4.18"


class TestClusterReduceShardMetaRecycle:
    def _storage(self, ip, port, host_id, machine=None):
        if machine is None:
            machine = SimpleNamespace(ip=ip, bk_host_id=host_id, bk_cloud_id=0, delete=MagicMock())
        storage = SimpleNamespace(
            machine=machine,
            bk_instance_id=0,
            proxyinstance_set=MagicMock(),
            bind_entry=MagicMock(),
            delete=MagicMock(),
        )
        storage.proxyinstance_set.clear = MagicMock()
        storage.bind_entry.all.return_value = []
        return storage, machine

    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.CcManage")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstanceTuple")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstance")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.Cluster")
    def test_recycle_when_machine_has_no_remaining_instance(
        self, mock_cluster_cls, mock_storage_cls, _mock_tuple, mock_cc_cls
    ):
        from backend.db_meta.api.cluster.mongocluster.reduce_shard import cluster_reduce_shard

        storage, machine = self._storage("127.0.0.1", 27001, 101)
        cluster = SimpleNamespace(
            id=1001,
            bk_biz_id=3,
            bk_cloud_id=0,
            cluster_type="MongoShardedCluster",
            immute_domain="demo.mongodb.db",
            nosqlstoragesetdtl_set=MagicMock(),
            storageinstance_set=MagicMock(),
        )
        cluster.nosqlstoragesetdtl_set.filter.return_value.delete.return_value = (1, {})
        cluster.storageinstance_set.get.return_value = storage
        mock_cluster_cls.objects.get.return_value = cluster
        mock_storage_cls.objects.filter.return_value.exists.return_value = False
        mock_cc = mock_cc_cls.return_value

        cluster_reduce_shard(
            bk_biz_id=3,
            cluster_id=1001,
            storages=[{"shard": "demo-s1", "nodes": [{"ip": "127.0.0.1", "port": 27001}]}],
            creator="tester",
            bk_cloud_id=0,
        )

        mock_cc.recycle_host.assert_called_once_with([101])
        machine.delete.assert_called_once()

    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.CcManage")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstanceTuple")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstance")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.Cluster")
    def test_skip_recycle_when_machine_still_has_instance(
        self, mock_cluster_cls, mock_storage_cls, _mock_tuple, mock_cc_cls
    ):
        from backend.db_meta.api.cluster.mongocluster.reduce_shard import cluster_reduce_shard

        storage, machine = self._storage("127.0.0.1", 27001, 101)
        cluster = SimpleNamespace(
            id=1001,
            bk_biz_id=3,
            bk_cloud_id=0,
            cluster_type="MongoShardedCluster",
            immute_domain="demo.mongodb.db",
            nosqlstoragesetdtl_set=MagicMock(),
            storageinstance_set=MagicMock(),
        )
        cluster.nosqlstoragesetdtl_set.filter.return_value.delete.return_value = (1, {})
        cluster.storageinstance_set.get.return_value = storage
        mock_cluster_cls.objects.get.return_value = cluster
        mock_storage_cls.objects.filter.return_value.exists.return_value = True
        mock_cc = mock_cc_cls.return_value

        cluster_reduce_shard(
            bk_biz_id=3,
            cluster_id=1001,
            storages=[{"shard": "demo-s1", "nodes": [{"ip": "127.0.0.1", "port": 27001}]}],
            creator="tester",
            bk_cloud_id=0,
        )

        mock_cc.recycle_host.assert_not_called()
        machine.delete.assert_not_called()

    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.CcManage")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstanceTuple")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.StorageInstance")
    @patch("backend.db_meta.api.cluster.mongocluster.reduce_shard.Cluster")
    def test_dedupe_machine_recycle_for_same_host(self, mock_cluster_cls, mock_storage_cls, _mock_tuple, mock_cc_cls):
        from backend.db_meta.api.cluster.mongocluster.reduce_shard import cluster_reduce_shard

        machine = SimpleNamespace(ip="127.0.0.1", bk_host_id=101, bk_cloud_id=0, delete=MagicMock())
        storage1, _ = self._storage("127.0.0.1", 27001, 101, machine=machine)
        storage2, _ = self._storage("127.0.0.1", 27002, 101, machine=machine)
        cluster = SimpleNamespace(
            id=1001,
            bk_biz_id=3,
            bk_cloud_id=0,
            cluster_type="MongoShardedCluster",
            immute_domain="demo.mongodb.db",
            nosqlstoragesetdtl_set=MagicMock(),
            storageinstance_set=MagicMock(),
        )
        cluster.nosqlstoragesetdtl_set.filter.return_value.delete.return_value = (1, {})
        cluster.storageinstance_set.get.side_effect = [storage1, storage2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_storage_cls.objects.filter.return_value.exists.return_value = False
        mock_cc = mock_cc_cls.return_value

        cluster_reduce_shard(
            bk_biz_id=3,
            cluster_id=1001,
            storages=[
                {
                    "shard": "demo-s1",
                    "nodes": [{"ip": "127.0.0.1", "port": 27001}, {"ip": "127.0.0.1", "port": 27002}],
                }
            ],
            creator="tester",
            bk_cloud_id=0,
        )

        mock_cc.recycle_host.assert_called_once_with([101])
        machine.delete.assert_called_once()
