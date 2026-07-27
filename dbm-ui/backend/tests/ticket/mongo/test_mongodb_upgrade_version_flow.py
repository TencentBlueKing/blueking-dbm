# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import ValidationError

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version import MongoUpgradeVersionFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.utils.mongodb.mongodb_repo import MongoNode, ReplicaSet
from backend.flow.utils.mongodb.version_utils import normalize_mongodb_full_version


class _FakeCluster:
    def __init__(self, cluster_id, cluster_type, major_version="mongodb-3.4.0"):
        self.cluster_id = cluster_id
        self.cluster_type = cluster_type
        self.bk_biz_id = 100
        self.name = "clu-{}".format(cluster_id)
        self.major_version = major_version

    def get_bk_cloud_id(self):
        return 0

    def get_iplist(self):
        return ["1.1.1.1", "1.1.1.2"]

    def get_shards(self, with_config=False, sort_by_set_name=False):
        nodes = [
            MongoNode(ip="1.1.1.2", port=27018, role="backup", bk_cloud_id=0, mtype="storage"),
            MongoNode(ip="1.1.1.1", port=27017, role="m1", bk_cloud_id=0, mtype="storage"),
        ]
        rs = ReplicaSet(set_type="replicaset", set_name="rs0", members=nodes)
        return [rs]

    def get_mongos(self):
        if self.cluster_type != ClusterType.MongoShardedCluster:
            return []
        return [
            MongoNode(ip="2.2.2.2", port=27019, role="mongos", bk_cloud_id=0, mtype="proxy"),
            MongoNode(ip="2.2.2.1", port=27019, role="mongos", bk_cloud_id=0, mtype="proxy"),
        ]

    def is_sharded_cluster(self):
        return self.cluster_type == ClusterType.MongoShardedCluster


def _payload():
    return {
        "uid": "u1",
        "ticket_id": "t1",
        "bk_biz_id": 100,
        "bk_cloud_id": 0,
        "ticket_type": "MONGODB_UPGRADE_VERSION",
        "created_by": "tester",
        "infos": [
            {
                "cluster_id_list": [1],
                "current_version": "3.4.0",
                "dest_version": "3.6.0",
                "strategy": "rolling",
                "bk_cloud_id": 0,
            }
        ],
    }


def _mock_pkg(version):
    # Persist path requires a resolvable full version; mocks use V1-style Package.version.
    try:
        full = normalize_mongodb_full_version(version)
    except ValueError:
        full = version
    return SimpleNamespace(path="mongodb.tgz", md5="mock-md5", version=full, db_version=None, db_version_id=None)


def test_serializer_reject_same_version():
    data = _payload()
    data["infos"][0]["dest_version"] = data["infos"][0]["current_version"]
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow.Serializer(data=data).is_valid(raise_exception=True)


def test_normalize_infos_for_replicaset(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {1: _FakeCluster(1, ClusterType.MongoReplicaSet)},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg(version),
    )

    flow = MongoUpgradeVersionFlow(root_id="r1", data=_payload())
    exec_groups = flow.cluster_infos[0]["exec_groups"]
    assert len(exec_groups["replicasets"]) == 1
    assert exec_groups["replicasets"][0]["members"][0].role == "backup"


def test_pipeline_contains_cluster_subflow(monkeypatch):
    fake_builder = MagicMock()
    fake_builder.add_parallel_acts = MagicMock()
    fake_builder.add_parallel_sub_pipeline = MagicMock()
    fake_builder.run_pipeline = MagicMock()
    fake_builder.run_pipeline_with_sidecar = MagicMock()

    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {1: _FakeCluster(1, ClusterType.MongoShardedCluster)},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg(version),
    )
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.version_utils.get_mongodb_package_v2_release",
        lambda pkg_type, series="latest": _mock_pkg(series),
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Builder",
        lambda **kwargs: fake_builder,
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoUtil.get_mongodb_os_conf",
        lambda self: {"file_path": "/data"},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.SendMedia.act",
        lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.GetFileList.mongodb_pkg",
        lambda self, db_version: [f"mongodb-{db_version}.tgz"],
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op.MongoUtil.get_mongo_user_password",
        lambda *args, **kwargs: ("mock-user", "mock-pwd"),
    )

    flow = MongoUpgradeVersionFlow(root_id="r1", data=_payload())
    flow.start()
    assert fake_builder.add_sub_pipeline.called
    assert fake_builder.add_parallel_acts.called
    fake_builder.run_pipeline.assert_called_once()
    fake_builder.run_pipeline_with_sidecar.assert_not_called()

    acts = fake_builder.add_parallel_acts.call_args[0][0]
    assert len(acts) == 1
    assert acts[0]["act_name"] == "MongoDB-升级介质下发"
    assert len(acts[0]["bk_host_list"]) == 2


def test_replace_package_payload_contains_current_and_dest_version():
    node = MongoNode(ip="1.1.1.1", port=27017, role="m1", bk_cloud_id=0, mtype="storage")
    kwargs = InstanceOpSubTask.make_replace_package_kwargs(
        file_path="/data",
        exec_node=node,
        current_version="3.4.0",
        dest_version="3.6.0",
        instance_type="mongod",
        pkg="mongodb.tgz",
        pkg_md5="abc",
    )
    payload = kwargs["db_act_template"]["payload"]
    assert payload["currentVersion"] == "3.4.0"
    assert payload["destVersion"] == "3.6.0"


def test_expand_upgrade_hops():
    assert MongoUpgradeVersionFlow._expand_upgrade_hops(
        "4.4", "6.0", current_full="mongodb-4.4.10", dest_full="mongodb-6.0.9"
    ) == [("4.4", "5.0"), ("5.0", "6.0")]


def test_expand_upgrade_hops_patch_same_major_minor():
    assert MongoUpgradeVersionFlow._expand_upgrade_hops(
        "6.0", "6.0", current_full="mongodb-6.0.6", dest_full="mongodb-6.0.27"
    ) == [("6.0", "6.0")]


def test_reject_patch_when_dest_not_higher():
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow._expand_upgrade_hops(
            "6.0", "6.0", current_full="mongodb-6.0.27", dest_full="mongodb-6.0.6"
        )


def test_patch_upgrade_flow_init_success(monkeypatch):
    data = _payload()
    data["infos"][0]["current_version"] = "mongodb-6.0.6"
    data["infos"][0]["dest_version"] = "mongodb-6.0.27"
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {1: _FakeCluster(1, ClusterType.MongoReplicaSet, major_version="mongodb-6.0.6")},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg("mongodb-6.0.27"),
    )

    flow = MongoUpgradeVersionFlow(root_id="r1", data=data)
    assert len(flow.cluster_infos) == 1
    hop_plan = flow.cluster_infos[0]["hop_plans"][0]
    assert hop_plan["hop_key"] == ("6.0", "6.0")
    assert hop_plan["current_version"] == "mongodb-6.0.6"
    assert hop_plan["dest_version"] == "mongodb-6.0.27"
    assert hop_plan["persist_version"] == "mongodb-6.0.27"


def test_get_target_package_for_exact_dest_version(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg("mongodb-6.0.27"),
    )
    pkg = MongoUpgradeVersionFlow._get_target_package_for_dest("mongodb-6.0.27")
    assert pkg.version == "mongodb-6.0.27"


def test_reject_inconsistent_upgrade_path_across_clusters(monkeypatch):
    data = _payload()
    data["infos"].append(
        {
            "cluster_id_list": [2],
            "current_version": "4.4.0",
            "dest_version": "5.0.0",
            "strategy": "rolling",
            "bk_cloud_id": 0,
        }
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {
            1: _FakeCluster(1, ClusterType.MongoReplicaSet),
            2: _FakeCluster(2, ClusterType.MongoReplicaSet),
        },
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg(version),
    )
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow(root_id="r1", data=data)


def test_reject_unsupported_version_chain(monkeypatch):
    data = _payload()
    data["infos"][0]["current_version"] = "2.6.18"
    data["infos"][0]["dest_version"] = "3.6.8"
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {1: _FakeCluster(1, ClusterType.MongoReplicaSet, major_version="mongodb-2.6.18")},
    )
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow(root_id="r1", data=data)


def test_multi_hop_media_contains_intermediate_versions(monkeypatch):
    data = _payload()
    data["infos"][0]["current_version"] = "4.4.10"
    data["infos"][0]["dest_version"] = "6.0.9"
    fake_builder = MagicMock()
    fake_builder.add_parallel_acts = MagicMock()
    fake_builder.add_parallel_sub_pipeline = MagicMock()
    fake_builder.run_pipeline = MagicMock()
    fake_builder.run_pipeline_with_sidecar = MagicMock()

    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoRepository.fetch_many_cluster_dict",
        lambda **kwargs: {1: _FakeCluster(1, ClusterType.MongoShardedCluster)},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: _mock_pkg(version),
    )
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.version_utils.get_mongodb_package_v2_release",
        lambda pkg_type, series="latest": _mock_pkg(series),
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Builder",
        lambda **kwargs: fake_builder,
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.MongoUtil.get_mongodb_os_conf",
        lambda self: {"file_path": "/data"},
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.SendMedia.act",
        lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.GetFileList.mongodb_pkg",
        lambda self, db_version: [f"{db_version}.tgz"],
    )
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op.MongoUtil.get_mongo_user_password",
        lambda *args, **kwargs: ("mock-user", "mock-pwd"),
    )

    flow = MongoUpgradeVersionFlow(root_id="r1", data=data)
    flow.start()
    # Top-level pipeline: pre-upgrade disk check, then one sub-pipeline per hop (4.4->5.0, 5.0->6.0).
    assert fake_builder.add_sub_pipeline.call_count == 3
    acts = fake_builder.add_parallel_acts.call_args[0][0]
    file_list = acts[0]["file_list"]
    # Hop dest major.minor resolves to full persist version via mock package.
    assert "mongodb-5.0.0.tgz" in file_list
    assert "mongodb-6.0.0.tgz" in file_list


def test_get_target_package_fallback_to_prefix_query(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: None,
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return _mock_pkg("3.6.18")

    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Package.objects",
        _FakeQuery(),
    )

    pkg = MongoUpgradeVersionFlow._get_target_package("3.6")
    assert pkg.version == "mongodb-3.6.18"


def test_get_target_package_fallback_match_mongodb_prefixed_version(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.lookup_mongodb_package",
        lambda version, package=None: None,
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return _mock_pkg("mongodb-3.6.23")

    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Package.objects",
        _FakeQuery(),
    )

    pkg = MongoUpgradeVersionFlow._get_target_package("3.6")
    assert pkg.version == "mongodb-3.6.23"


def test_normalize_mongodb_full_version():
    assert normalize_mongodb_full_version("5.0.14") == "mongodb-5.0.14"
    assert normalize_mongodb_full_version("mongodb-5.0.14") == "mongodb-5.0.14"
    assert normalize_mongodb_full_version("MongoDB-5.0.14") == "mongodb-5.0.14"
    assert normalize_mongodb_full_version("5.0.14-rc1") == "mongodb-5.0.14-rc1"
    with pytest.raises(ValueError):
        normalize_mongodb_full_version("monogdb-5.0.14")


def test_resolve_persist_version_prefers_pkg():
    pkg = _mock_pkg("mongodb-5.0.14")
    assert MongoUpgradeVersionFlow._resolve_persist_version(pkg, "5.0") == "mongodb-5.0.14"


def test_resolve_persist_version_series_pkg_uses_db_version(monkeypatch):
    pkg = SimpleNamespace(
        version="mongodb-7.0",
        db_version=SimpleNamespace(base_version="7.0.28", name="mongodb-7.0.28"),
        db_version_id=14,
    )
    # Force primary path to fail so fallback uses _resolve_package_full_version
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.resolve_mongodb_persist_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    assert MongoUpgradeVersionFlow._resolve_persist_version(pkg, "mongodb-7.0") == "mongodb-7.0.28"


def test_resolve_persist_version_series_pkg_without_db_version_raises(monkeypatch):
    pkg = SimpleNamespace(version="mongodb-7.0", db_version=None, db_version_id=None)
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.resolve_mongodb_persist_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow._resolve_persist_version(pkg, "mongodb-7.0")


def test_reject_version_beyond_chain():
    with pytest.raises(ValidationError):
        MongoUpgradeVersionFlow._expand_upgrade_hops(
            "8.0", "9.0", current_full="mongodb-8.0.0", dest_full="mongodb-9.0.0"
        )


def test_expand_upgrade_hops_70_to_80():
    hops = MongoUpgradeVersionFlow._expand_upgrade_hops(
        "7.0", "8.0", current_full="mongodb-7.0.14", dest_full="mongodb-8.0.0"
    )
    assert hops == [("7.0", "8.0")]


def test_protocol_upgrade_needed_only_for_36_to_40():
    assert MongoUpgradeVersionFlow._protocol_upgrade_needed("3.6", "4.0") is True
    assert MongoUpgradeVersionFlow._protocol_upgrade_needed("mongodb-3.6", "mongodb-4.0.0") is True
    assert MongoUpgradeVersionFlow._protocol_upgrade_needed("3.4", "3.6") is False
    assert MongoUpgradeVersionFlow._protocol_upgrade_needed("3.6", "3.6") is False
    assert MongoUpgradeVersionFlow._protocol_upgrade_needed("4.0", "4.2") is False


def test_build_upgrade_rs_protocol_acts_one_per_replicaset(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.sub_task.upgrade_version.MongoUtil.get_mongo_user_password",
        lambda *args, **kwargs: ("dba", "pwd"),
    )
    node = SimpleNamespace(ip="1.1.1.1", port=27001, bk_cloud_id=0)
    exec_groups = {
        "replicasets": [
            {"name": "rs1", "members": [node]},
            {"name": "rs2", "members": [node]},
        ]
    }
    acts = MongoUpgradeVersionFlow._build_upgrade_rs_protocol_acts(exec_groups, "/data")
    assert len(acts) == 2
    assert acts[0]["act_name"] == "MongoDB-升级复制协议版本-rs1"
    assert acts[0]["kwargs"]["db_act_template"]["action"] == "mongo_upgrade_rs_protocol"
    assert acts[0]["kwargs"]["db_act_template"]["payload"]["targetProtocolVersion"] == 1
