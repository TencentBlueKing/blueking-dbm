# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta import MongoScaleReplsMetaService


@patch("backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta.CcManage")
@patch("backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta.StorageInstanceTuple")
@patch(
    "backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta.machine_has_remaining_instance",
    return_value=True,
)
def test_scale_in_repls_keeps_machine_with_remaining_mongos(mock_has_remaining, mock_tuple, mock_cc_cls):
    machine = SimpleNamespace(ip="127.0.0.1", bk_host_id=101, delete=MagicMock())
    storage = SimpleNamespace(
        machine=machine,
        port=27001,
        bk_instance_id=10001,
        instance_role="mongo_m2",
        bind_entry=MagicMock(),
        delete=MagicMock(),
    )
    storage.bind_entry.all.return_value = []
    cluster = SimpleNamespace(
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster_type="MongoShardedCluster",
        storageinstance_set=MagicMock(),
    )
    cluster.storageinstance_set.get.return_value = storage

    MongoScaleReplsMetaService.scale_in_repls.__wrapped__(
        MongoScaleReplsMetaService(),
        cluster,
        [{"ip": "127.0.0.1", "port": 27001}],
        "tester",
    )

    mock_tuple.objects.get.return_value.delete.assert_called_once()
    mock_has_remaining.assert_called_once_with("127.0.0.1", 3, 0)
    mock_cc_cls.return_value.recycle_host.assert_not_called()
    machine.delete.assert_not_called()
