# -*- coding: utf-8 -*-

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.consts import MongoDBClusterRole
from backend.flow.utils.mongodb.restart_target_resolver import (
    RestartTargetNode,
    dedupe_restart_targets,
    group_restart_targets_by_cluster,
    order_rs_members,
    order_rs_members_by_meta_role,
)


def _node(ip, port, role, cluster_id=1, set_name="rs0", rs_type=MongoDBClusterRole.Replicaset.value, is_mongos=False):
    return RestartTargetNode(
        ip=ip,
        port=port,
        role=role,
        bk_cloud_id=0,
        machine_type="mongodb",
        cluster_id=cluster_id,
        cluster_type=ClusterType.MongoReplicaSet.value,
        set_name=set_name,
        rs_type=rs_type,
        is_mongos=is_mongos,
    )


def test_dedupe_restart_targets():
    nodes = [
        _node("1.1.1.1", 27017, InstanceRole.MONGO_M1.value),
        _node("1.1.1.1", 27017, InstanceRole.MONGO_M1.value),
        _node("1.1.1.2", 27018, InstanceRole.MONGO_M2.value),
    ]
    result = dedupe_restart_targets(nodes)
    assert len(result) == 2
    assert {n.addr() for n in result} == {"1.1.1.1:27017", "1.1.1.2:27018"}


def test_order_rs_members_by_meta_role():
    nodes = [
        _node("1.1.1.3", 27019, InstanceRole.MONGO_M2.value),
        _node("1.1.1.2", 27018, InstanceRole.MONGO_M1.value),
        _node("1.1.1.1", 27017, InstanceRole.MONGO_BACKUP.value),
    ]
    ordered = order_rs_members_by_meta_role(nodes)
    assert [n.role for n in ordered] == [
        InstanceRole.MONGO_BACKUP.value,
        InstanceRole.MONGO_M1.value,
        InstanceRole.MONGO_M2.value,
    ]


def test_order_rs_members_defers_ext_primary(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.restart_target_resolver._detect_primary_addrs_from_ext",
        lambda nodes: {("1.1.1.2", 27018)},
    )
    nodes = [
        _node("1.1.1.3", 27019, InstanceRole.MONGO_M2.value),
        _node("1.1.1.2", 27018, InstanceRole.MONGO_M1.value),
        _node("1.1.1.1", 27017, InstanceRole.MONGO_BACKUP.value),
    ]
    for force in (False, True):
        ordered = order_rs_members(nodes, force=force)
        assert [n.addr() for n in ordered] == ["1.1.1.1:27017", "1.1.1.3:27019", "1.1.1.2:27018"]


def test_order_rs_members_without_ext_primary_uses_meta_role(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.mongodb.restart_target_resolver._detect_primary_addrs_from_ext",
        lambda nodes: set(),
    )
    nodes = [
        _node("1.1.1.3", 27019, InstanceRole.MONGO_M2.value),
        _node("1.1.1.2", 27018, InstanceRole.MONGO_M1.value),
        _node("1.1.1.1", 27017, InstanceRole.MONGO_BACKUP.value),
    ]
    for force in (False, True):
        ordered = order_rs_members(nodes, force=force)
        assert [n.addr() for n in ordered] == ["1.1.1.1:27017", "1.1.1.2:27018", "1.1.1.3:27019"]


def test_instance_restart_payload_serializer_requires_valid_info():
    from backend.flow.utils.mongodb.restart_target_resolver import InstanceRestartPayloadSerializer

    serializer = InstanceRestartPayloadSerializer(
        data={
            "created_by": "tester",
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "infos": [{}],
        }
    )
    assert not serializer.is_valid()
    assert "infos" in serializer.errors


def test_instance_restart_payload_accepts_mixed_info_kinds():
    from backend.flow.utils.mongodb.restart_target_resolver import InstanceRestartPayloadSerializer

    serializer = InstanceRestartPayloadSerializer(
        data={
            "created_by": "tester",
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "infos": [
                {"cluster_id": 19},
                {"ip": "127.0.0.1", "port": 27001, "cluster_id": 19},
            ],
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["infos"][0]["info_kind"] == "cluster"
    assert serializer.validated_data["infos"][1]["info_kind"] == "explicit"


def test_instance_restart_payload_infers_bk_cloud_id_from_infos():
    from backend.flow.utils.mongodb.restart_target_resolver import InstanceRestartPayloadSerializer

    serializer = InstanceRestartPayloadSerializer(
        data={
            "created_by": "tester",
            "bk_biz_id": 1,
            "infos": [
                {"ip": "127.0.0.1", "port": 27001, "cluster_id": 19, "bk_cloud_id": 0},
            ],
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["bk_cloud_id"] == 0


def test_instance_restart_payload_uid_accepts_int():
    from backend.flow.utils.mongodb.restart_target_resolver import InstanceRestartPayloadSerializer

    serializer = InstanceRestartPayloadSerializer(
        data={
            "uid": 12345,
            "created_by": "tester",
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "infos": [{"cluster_id": 19}],
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["uid"] == "12345"


def test_instance_restart_info_serializer_modes():
    from backend.flow.utils.mongodb.restart_target_resolver import (
        INFO_KIND_CLUSTER,
        INFO_KIND_EXPLICIT,
        INFO_KIND_INSTANCE,
        INFO_KIND_IP,
        InstanceRestartInfoSerializer,
    )

    explicit = InstanceRestartInfoSerializer(data={"ip": "127.0.0.1", "port": 27001, "cluster_id": 19})
    assert explicit.is_valid(), explicit.errors
    assert explicit.validated_data["info_kind"] == INFO_KIND_EXPLICIT

    cluster = InstanceRestartInfoSerializer(data={"cluster_id": 19})
    assert cluster.is_valid(), cluster.errors
    assert cluster.validated_data["info_kind"] == INFO_KIND_CLUSTER

    ip_only = InstanceRestartInfoSerializer(data={"ip": "127.0.0.1"})
    assert ip_only.is_valid(), ip_only.errors
    assert ip_only.validated_data["info_kind"] == INFO_KIND_IP

    instance = InstanceRestartInfoSerializer(data={"instance": "127.0.0.1:27001"})
    assert instance.is_valid(), instance.errors
    assert instance.validated_data["info_kind"] == INFO_KIND_INSTANCE


def test_instance_restart_info_rejects_ambiguous_fields():
    from backend.flow.utils.mongodb.restart_target_resolver import InstanceRestartInfoSerializer

    serializer = InstanceRestartInfoSerializer(data={"cluster_id": 19, "ip": "127.0.0.1"})
    assert not serializer.is_valid()


def test_resolve_restart_targets_from_infos_explicit(monkeypatch):
    from backend.flow.utils.mongodb import restart_target_resolver as resolver

    target = _node("127.0.0.1", 27001, InstanceRole.MONGO_M1.value, cluster_id=19)

    class FakeCluster:
        bk_biz_id = 1
        bk_cloud_id = 0
        cluster_id = 19

    monkeypatch.setattr(
        resolver.MongoRepository,
        "fetch_one_cluster",
        lambda id: FakeCluster() if id == 19 else None,
    )
    monkeypatch.setattr(resolver, "_nodes_from_cluster", lambda cluster: [target])

    nodes = resolver.resolve_restart_targets_from_infos(
        [{"info_kind": "explicit", "ip": "127.0.0.1", "port": 27001, "cluster_id": 19}],
        bk_biz_id=1,
        bk_cloud_id=0,
    )
    assert len(nodes) == 1
    assert nodes[0].addr() == "127.0.0.1:27001"


def test_resolve_restart_targets_from_infos_cluster_dedupe(monkeypatch):
    from backend.flow.utils.mongodb import restart_target_resolver as resolver

    target = _node("127.0.0.1", 27001, InstanceRole.MONGO_M1.value, cluster_id=19)

    monkeypatch.setattr(resolver, "_resolve_cluster_id", lambda cluster_id, bk_biz_id, bk_cloud_id: [target])
    monkeypatch.setattr(
        resolver,
        "_resolve_explicit_instance",
        lambda ip, port, cluster_id, bk_biz_id, bk_cloud_id: [target],
    )

    nodes = resolver.resolve_restart_targets_from_infos(
        [
            {"info_kind": "cluster", "cluster_id": 19},
            {"info_kind": "explicit", "ip": "127.0.0.1", "port": 27001, "cluster_id": 19},
        ],
        bk_biz_id=1,
        bk_cloud_id=0,
    )
    assert len(nodes) == 1


def test_group_restart_targets_by_cluster_splits_shard_config_mongos():
    nodes = [
        RestartTargetNode(
            ip="1.1.1.1",
            port=27017,
            role=InstanceRole.MONGO_M1.value,
            bk_cloud_id=0,
            machine_type="mongodb",
            cluster_id=100,
            cluster_type=ClusterType.MongoShardedCluster.value,
            set_name="s1",
            rs_type=MongoDBClusterRole.ShardSvr.value,
            is_mongos=False,
        ),
        RestartTargetNode(
            ip="2.2.2.2",
            port=27018,
            role=InstanceRole.MONGO_M1.value,
            bk_cloud_id=0,
            machine_type="mongodb",
            cluster_id=100,
            cluster_type=ClusterType.MongoShardedCluster.value,
            set_name="config",
            rs_type=MongoDBClusterRole.ConfigSvr.value,
            is_mongos=False,
        ),
        RestartTargetNode(
            ip="3.3.3.3",
            port=27019,
            role=MongoDBClusterRole.Mongos.value,
            bk_cloud_id=0,
            machine_type="proxy",
            cluster_id=100,
            cluster_type=ClusterType.MongoShardedCluster.value,
            set_name="",
            rs_type="",
            is_mongos=True,
        ),
    ]
    plans = group_restart_targets_by_cluster(nodes)
    plan = plans[100]
    assert len(plan.shard_rs) == 1
    assert len(plan.config_rs) == 1
    assert len(plan.mongos) == 1


def test_batch_get_restart_node_credentials(monkeypatch):
    from backend.flow.utils.mongodb import restart_target_resolver as resolver

    nodes = [
        _node("1.1.1.1", 27017, InstanceRole.MONGO_M1.value),
        _node("1.1.1.2", 27018, InstanceRole.MONGO_M2.value),
    ]

    def fake_get_users_password_from_db(self, instances, usernames):
        assert len(instances) == 2
        assert usernames == ["dba"]
        return {
            "password": [
                {"ip": "1.1.1.1", "port": 27017, "bk_cloud_id": 0, "username": "dba", "password": "pwd1"},
                {"ip": "1.1.1.2", "port": 27018, "bk_cloud_id": 0, "username": "dba", "password": "pwd2"},
            ],
            "info": None,
        }

    monkeypatch.setattr(
        resolver.MongoDBPassword,
        "get_users_password_from_db",
        fake_get_users_password_from_db,
    )

    creds = resolver.batch_get_restart_node_credentials(nodes)
    assert creds[(0, "1.1.1.1", 27017)] == ("dba", "pwd1")
    assert creds[(0, "1.1.1.2", 27018)] == ("dba", "pwd2")
