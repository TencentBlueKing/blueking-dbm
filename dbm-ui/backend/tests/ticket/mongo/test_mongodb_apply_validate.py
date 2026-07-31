# -*- coding: utf-8 -*-
"""MongoDB 副本集 / 分片集群部署单据参数合法性校验。"""
import copy

import pytest
from rest_framework.exceptions import ValidationError

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.builders.mongodb.mongo_replicaset_apply import MongoReplicaSetApplyDetailSerializer
from backend.ticket.builders.mongodb.mongo_shard_apply import MongoShardedClusterApplyDetailSerializer
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db


def _replicaset_payload(**overrides):
    data = {
        "bk_cloud_id": 0,
        "db_app_abbr": "dba",
        "city_code": "default",
        "disaster_tolerance_level": AffinityEnum.NONE.value,
        "cluster_type": ClusterType.MongoReplicaSet.value,
        "db_version": "mongodb-6.0.27",
        "start_port": 27001,
        "replica_count": 2,
        "node_count": 3,
        "node_replica_count": 2,
        "replica_sets": [
            {"set_id": "rs0", "name": "rs0", "domain": "m1.rs0.dba.db"},
            {"set_id": "rs1", "name": "rs1", "domain": "m1.rs1.dba.db"},
        ],
        "spec_id": 1,
        "oplog_percent": 10,
        "ip_source": IpSource.RESOURCE_POOL.value,
        "resource_spec": {"mongo_machine_set": {"spec_id": 1, "count": 3}},
    }
    data.update(overrides)
    return data


def _shard_payload(**overrides):
    data = {
        "bk_cloud_id": 0,
        "db_app_abbr": "dba",
        "city_code": "default",
        "disaster_tolerance_level": AffinityEnum.NONE.value,
        "cluster_type": ClusterType.MongoShardedCluster.value,
        "cluster_name": "shard1",
        "cluster_alias": "shard1",
        "db_version": "mongodb-6.0.27",
        "start_port": 27017,
        "oplog_percent": 10,
        "ip_source": IpSource.RESOURCE_POOL.value,
        "shard_machine_group": 2,
        "shard_num": 2,
        "resource_spec": {
            "mongodb": {"spec_id": 1, "count": 6},
            "mongo_config": {"spec_id": 1, "count": 3},
            "mongos": {"spec_id": 1, "count": 2},
        },
    }
    data.update(overrides)
    return data


def _assert_valid(serializer_cls, data, ticket_type):
    ser = serializer_cls(data=data, context={"ticket_type": ticket_type})
    assert ser.is_valid(raise_exception=True)


def _assert_invalid(serializer_cls, data, ticket_type, msg_part=None):
    ser = serializer_cls(data=data, context={"ticket_type": ticket_type})
    with pytest.raises(ValidationError) as exc:
        ser.is_valid(raise_exception=True)
    if msg_part:
        assert msg_part in str(exc.value)


def test_replicaset_apply_accepts_divisible_counts():
    _assert_valid(
        MongoReplicaSetApplyDetailSerializer,
        _replicaset_payload(),
        TicketType.MONGODB_REPLICASET_APPLY,
    )


def test_replicaset_apply_rejects_not_divisible():
    # ticket 5538 同类：1 套副本集却要求单机 2 套 → groups=0
    data = _replicaset_payload(
        replica_count=1,
        node_replica_count=2,
        replica_sets=[{"set_id": "rs0", "name": "rs0", "domain": "m1.rs0.dba.db"}],
    )
    _assert_invalid(
        MongoReplicaSetApplyDetailSerializer,
        data,
        TicketType.MONGODB_REPLICASET_APPLY,
        msg_part="整除",
    )


def test_replicaset_apply_rejects_replica_sets_len_mismatch():
    data = _replicaset_payload(replica_count=2, node_replica_count=1)
    data["replica_sets"] = [{"set_id": "rs0", "name": "rs0", "domain": "m1.rs0.dba.db"}]
    _assert_invalid(
        MongoReplicaSetApplyDetailSerializer,
        data,
        TicketType.MONGODB_REPLICASET_APPLY,
        msg_part="不一致",
    )


def test_replicaset_apply_rejects_non_positive_node_count():
    _assert_invalid(
        MongoReplicaSetApplyDetailSerializer,
        _replicaset_payload(node_count=0),
        TicketType.MONGODB_REPLICASET_APPLY,
        msg_part="node_count",
    )


def test_shard_apply_accepts_divisible_counts():
    _assert_valid(
        MongoShardedClusterApplyDetailSerializer,
        _shard_payload(),
        TicketType.MONGODB_SHARD_APPLY,
    )


def test_shard_apply_rejects_shard_num_not_divisible():
    data = _shard_payload(shard_num=1, shard_machine_group=2)
    _assert_invalid(
        MongoShardedClusterApplyDetailSerializer,
        data,
        TicketType.MONGODB_SHARD_APPLY,
        msg_part="整除",
    )


def test_shard_apply_rejects_mongodb_count_not_divisible():
    data = _shard_payload()
    data = copy.deepcopy(data)
    data["resource_spec"]["mongodb"]["count"] = 5  # 5 % 2 != 0
    _assert_invalid(
        MongoShardedClusterApplyDetailSerializer,
        data,
        TicketType.MONGODB_SHARD_APPLY,
        msg_part="mongodb",
    )


def test_shard_apply_rejects_configsvr_when_shardsvr_multi_member():
    # mongodb.count=6, group=2 → members=3，config 必须为 3；改为 1 应失败
    data = copy.deepcopy(_shard_payload())
    data["resource_spec"]["mongo_config"]["count"] = 1
    _assert_invalid(
        MongoShardedClusterApplyDetailSerializer,
        data,
        TicketType.MONGODB_SHARD_APPLY,
        msg_part="configsvr",
    )
