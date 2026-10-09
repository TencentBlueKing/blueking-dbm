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
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta import ExecAddRelationshipOperation


class FakeData:
    def __init__(self, kwargs):
        self.inputs = {"kwargs": kwargs, "global_data": {}}

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _make_service():
    svc = ExecAddRelationshipOperation()
    svc._runtime_attrs = {"root_pipeline_id": "root123", "id": "node1", "version": "v1"}
    svc.log_info = MagicMock()
    svc.log_warning = MagicMock()
    svc.log_error = MagicMock()
    return svc


def _replicaset_kwargs():
    return {
        "cluster_type": ClusterType.MongoReplicaSet.value,
        "bk_biz_id": 1,
        "name": "rs1",
        "immute_domain": "rs1.db",
        "alias": "rs1",
        "major_version": "mongodb-6.0.5",
        "storages": [],
        "creator": "admin",
        "bk_cloud_id": 0,
        "db_module_id": 0,
        "region": "sz",
        "skip_machine": False,
        "spec_id": 1,
        "spec_config": {},
        "disaster_tolerance_level": "NONE",
        "zone_list": [],
    }


def _shard_kwargs():
    return {
        "cluster_type": ClusterType.MongoShardedCluster.value,
        "bk_biz_id": 1,
        "name": "sc1",
        "immute_domain": "sc1.db",
        "alias": "sc1",
        "db_module_id": 0,
        "major_version": "mongodb-6.0.5",
        "proxies": [],
        "configs": [],
        "storages": [],
        "creator": "admin",
        "bk_cloud_id": 0,
        "region": "sz",
        "machine_specs": {},
        "disaster_tolerance_level": "NONE",
        "zone_list": [],
    }


class TestAddRelationshipProgressCallback:
    @patch("backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta.pkg_create_mongoset")
    def test_replicaset_passes_progress_callback(self, mock_pkg):
        svc = _make_service()
        result = svc._execute(FakeData(_replicaset_kwargs()), None)
        assert result is True
        assert mock_pkg.call_args.kwargs["progress_callback"] is svc.log_info
        svc.log_info.assert_any_call(
            "start add mongodb relationship to meta, cluster_type={}, name={}".format(
                ClusterType.MongoReplicaSet.value, "rs1"
            )
        )
        svc.log_info.assert_any_call("add mongodb relationship to meta successfully")

    @patch("backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta.pkg_create_mongo_cluster")
    def test_shard_passes_progress_callback(self, mock_pkg):
        svc = _make_service()
        result = svc._execute(FakeData(_shard_kwargs()), None)
        assert result is True
        assert mock_pkg.call_args.kwargs["progress_callback"] is svc.log_info

    @patch(
        "backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta.pkg_create_mongoset",
        side_effect=Exception("boom"),
    )
    def test_failure_logs_error(self, mock_pkg):
        svc = _make_service()
        result = svc._execute(FakeData(_replicaset_kwargs()), None)
        assert result is False
        svc.log_error.assert_called()
        assert "boom" in svc.log_error.call_args[0][0]
