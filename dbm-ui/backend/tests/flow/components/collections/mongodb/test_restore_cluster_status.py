# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.flow.plugins.components.collections.mongodb.restore_cluster_status import restore_mongo_cluster_status

pytestmark = pytest.mark.django_db


def _cluster(status, storage_not_running=False, proxy_not_running=False, has_storage=True, has_proxy=False):
    storage = MagicMock()
    storage.exists.return_value = has_storage
    storage.exclude.return_value.exists.return_value = storage_not_running
    proxy = MagicMock()
    proxy.exists.return_value = has_proxy
    proxy.exclude.return_value.exists.return_value = proxy_not_running
    cluster = MagicMock()
    cluster.id = 9
    cluster.status = status
    cluster.storageinstance_set = storage
    cluster.proxyinstance_set = proxy
    return cluster


class TestRestoreMongoClusterStatus:
    def test_sets_normal_when_all_instances_running(self):
        cluster = _cluster("abnormal")
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter",
            return_value=[cluster],
        ):
            updated = restore_mongo_cluster_status([9])
        assert updated == [9]
        assert cluster.status == "normal"
        cluster.save.assert_called_once_with(update_fields=["status"])

    def test_keeps_status_when_any_instance_not_running(self):
        cluster = _cluster("abnormal", storage_not_running=True)
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter",
            return_value=[cluster],
        ):
            updated = restore_mongo_cluster_status([9])
        assert updated == []
        cluster.save.assert_not_called()

    def test_mongos_not_running_blocks_restore(self):
        cluster = _cluster("abnormal", has_proxy=True, proxy_not_running=True)
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter",
            return_value=[cluster],
        ):
            updated = restore_mongo_cluster_status([9])
        assert updated == []
        cluster.save.assert_not_called()

    def test_skips_temporary_cluster(self):
        cluster = _cluster("temporary")
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter",
            return_value=[cluster],
        ):
            updated = restore_mongo_cluster_status([9])
        assert updated == []
        cluster.save.assert_not_called()

    def test_already_normal_does_not_save(self):
        cluster = _cluster("normal")
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter",
            return_value=[cluster],
        ):
            updated = restore_mongo_cluster_status([9])
        assert updated == []
        cluster.save.assert_not_called()

    def test_empty_cluster_ids_skips_query(self):
        with patch(
            "backend.flow.plugins.components.collections.mongodb.restore_cluster_status.Cluster.objects.filter"
        ) as objects_filter:
            updated = restore_mongo_cluster_status([])
        assert updated == []
        objects_filter.assert_not_called()


class TestEnsureStartFlowClusterStatusStep:
    def test_appends_restore_act_after_instance_subflows(self):
        from backend.flow.engine.bamboo.scene.mongodb.mongodb_instance_ensure_start import MongoDBInstanceEnsureFlow

        target = SimpleNamespace(ip="127.0.0.1", port=27017, cluster_id=9)
        builder = MagicMock()
        flow = MongoDBInstanceEnsureFlow(
            "root-id",
            {
                "uid": "mongo-ensure-3-20261010-001",
                "bk_biz_id": 3,
                "bk_cloud_id": 0,
                "infos": [{"ip": "127.0.0.1", "port": 27017, "cluster_id": 9, "bk_cloud_id": 0}],
            },
        )
        module = "backend.flow.engine.bamboo.scene.mongodb.mongodb_instance_ensure_start"
        with patch(f"{module}.resolve_restart_targets_from_infos", return_value=[target]), patch(
            f"{module}.batch_get_restart_node_credentials", return_value={}
        ), patch(f"{module}.MongoUtil") as mongo_util, patch(f"{module}.GetFileList") as get_file_list, patch(
            f"{module}.collect_hosts", return_value=[]
        ), patch(
            f"{module}.Builder", return_value=builder
        ), patch.object(
            flow, "_build_node_ensure_subflow", return_value="sub"
        ):
            mongo_util.return_value.get_mongodb_os_conf.return_value = {"file_path": "/data"}
            get_file_list.return_value.mongodb_actuator_pkg.return_value = []
            flow.start()

        builder.add_sub_pipeline.assert_called_once()
        act = builder.add_act.call_args.kwargs
        assert act["act_component_code"] == "restore_mongo_cluster_status"
        assert act["kwargs"]["cluster_ids"] == [9]
        builder.run_pipeline.assert_called_once()
