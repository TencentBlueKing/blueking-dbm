# -*- coding: utf-8 -*-
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version import MongoUpgradeVersionFlow
from backend.flow.utils.mongodb.mongodb_repo import MongoNode


def _exec_groups_with_mongos():
    return {
        "replicasets": [
            {
                "members": [
                    MongoNode("127.0.0.1", 27017, MongoDBClusterRole.Replicaset.value, 0, ""),
                ]
            }
        ],
        "mongos": [
            MongoNode("127.0.0.2", 27021, MongoDBClusterRole.Mongos.value, 0, ""),
        ],
    }


def test_collect_all_nodes_includes_mongos_for_precheck_upgrade():
    nodes = MongoUpgradeVersionFlow._collect_all_nodes(_exec_groups_with_mongos())
    roles = {node.role for node in nodes}
    assert MongoDBClusterRole.Mongos.value in roles
    assert MongoDBClusterRole.Replicaset.value in roles
    assert len(nodes) == 2
