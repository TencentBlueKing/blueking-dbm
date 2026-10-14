# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest
from rest_framework import serializers

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


class _MachineRows(list):
    def only(self, *_fields):
        return self


@pytest.mark.parametrize("os_name", ["tlinux-4", "tlinux-4.4"])
def test_validate_tlinux4_hosts_accepts_supported_os(monkeypatch, os_name):
    node = MongoNode("127.0.0.1", 27017, MongoDBClusterRole.Replicaset.value, 0, "")
    rows = _MachineRows([SimpleNamespace(ip=node.ip, bk_cloud_id=node.bk_cloud_id, bk_os_name=os_name)])
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Machine.objects.filter",
        lambda **_kwargs: rows,
    )
    MongoUpgradeVersionFlow._validate_tlinux4_hosts([node])


def test_validate_tlinux4_hosts_rejects_old_os(monkeypatch):
    node = MongoNode("127.0.0.2", 27017, MongoDBClusterRole.Replicaset.value, 0, "")
    rows = _MachineRows([SimpleNamespace(ip=node.ip, bk_cloud_id=node.bk_cloud_id, bk_os_name="tlinux-2.6")])
    monkeypatch.setattr(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version.Machine.objects.filter",
        lambda **_kwargs: rows,
    )
    with pytest.raises(serializers.ValidationError, match="tlinux4"):
        MongoUpgradeVersionFlow._validate_tlinux4_hosts([node])
