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

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mongodb.mongo_shutdown_meta import MongosShutdownMetaService


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs

    def get_one_of_inputs(self, key):
        return self.inputs[key]


def _build_cluster(
    cluster_id=59,
    domain="m1.cyc30rs1.dba.db",
    cluster_type="MongoReplicaSet",
    phase="offline",
    major_version="mongodb-4.0",
    proxy_rows=None,
    storage_rows=None,
    entry_rows=None,
):
    proxy_rows = proxy_rows or []
    storage_rows = storage_rows or [
        {"port": 27001, "machine__ip": "127.0.0.1"},
        {"port": 27001, "machine__ip": "127.0.0.2"},
    ]
    entry_rows = entry_rows or [
        {"cluster_entry_type": "dns", "entry": domain, "role": "master_entry"},
    ]

    proxy_qs = MagicMock()
    proxy_qs.values.return_value = proxy_rows
    proxy_qs.all.return_value = []

    storage_qs = MagicMock()
    storage_qs.values.return_value = storage_rows
    storage_qs.all.return_value = []

    entry_qs = MagicMock()
    entry_qs.values.return_value = entry_rows
    entry_qs.filter.return_value.exists.return_value = False
    entry_qs.all.return_value = []

    cluster = SimpleNamespace(
        id=cluster_id,
        immute_domain=domain,
        name="dba-cyc30rs1",
        cluster_type=cluster_type,
        phase=phase,
        major_version=major_version,
        bk_biz_id=3,
        proxyinstance_set=proxy_qs,
        storageinstance_set=storage_qs,
        clusterentry_set=entry_qs,
        delete=MagicMock(),
    )
    return cluster


def test_snapshot_cluster_meta_collects_instances_and_entries():
    cluster = _build_cluster()

    snapshot = MongosShutdownMetaService._snapshot_cluster_meta(cluster)

    assert snapshot == {
        "cluster_id": 59,
        "domain": "m1.cyc30rs1.dba.db",
        "name": "dba-cyc30rs1",
        "cluster_type": "MongoReplicaSet",
        "phase": "offline",
        "major_version": "mongodb-4.0",
        "proxies": [],
        "storages": [
            {"ip": "127.0.0.1", "port": 27001},
            {"ip": "127.0.0.2", "port": 27001},
        ],
        "entries": [{"type": "dns", "entry": "m1.cyc30rs1.dba.db", "role": "master_entry"}],
    }


def test_log_shutdown_plan_writes_flow_log_lines():
    service = MongosShutdownMetaService()
    snapshot = {
        "cluster_id": 59,
        "domain": "m1.cyc30rs1.dba.db",
        "name": "dba-cyc30rs1",
        "cluster_type": "MongoReplicaSet",
        "phase": "offline",
        "major_version": "mongodb-4.0",
        "proxies": [],
        "storages": [{"ip": "127.0.0.1", "port": 27001}],
        "entries": [{"type": "dns", "entry": "m1.cyc30rs1.dba.db", "role": "master_entry"}],
    }

    with patch.object(service, "log_info") as mock_log_info:
        service._log_shutdown_plan(snapshot)

    detail_log = mock_log_info.call_args.args[0]
    assert "[mongo meta shutdown] cluster=m1.cyc30rs1.dba.db (id=59)" in detail_log
    assert "major_version: mongodb-4.0" in detail_log
    assert "storage 127.0.0.1:27001" in detail_log
    assert "entry [dns] m1.cyc30rs1.dba.db (master_entry)" in detail_log


@patch("backend.flow.plugins.components.collections.mongodb.mongo_shutdown_meta.CcManage")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_shutdown_meta.Cluster.objects.get")
def test_execute_logs_plan_and_summary(mock_cluster_get, _mock_cc_manage):
    cluster = _build_cluster()
    mock_cluster_get.return_value = cluster

    service = MongosShutdownMetaService()
    data = FakeData(
        inputs={
            "kwargs": {"bk_biz_id": 3, "cluster_id": 59, "created_by": "admin"},
            "global_data": {"job_root_id": "root-1"},
        }
    )

    with patch.object(service, "decommission_backends"):
        with patch.object(service, "log_info") as mock_log_info:
            assert service._execute(data, parent_data=None) is True

    assert mock_log_info.call_count == 2
    plan_log = mock_log_info.call_args_list[0].args[0]
    summary_log = mock_log_info.call_args_list[1].args[0]
    assert "[mongo meta shutdown] cluster=m1.cyc30rs1.dba.db (id=59)" in plan_log
    assert "mongo meta shutdown done: cluster=m1.cyc30rs1.dba.db (id=59)" in summary_log
    assert "removed proxy=0, storage=2, entry=1" in summary_log
    cluster.delete.assert_called_once()


@patch("backend.flow.plugins.components.collections.mongodb.mongo_shutdown_meta.Cluster.objects.get")
def test_execute_skips_when_cluster_already_absent(mock_cluster_get):
    mock_cluster_get.side_effect = Cluster.DoesNotExist("missing")

    service = MongosShutdownMetaService()
    data = FakeData(
        inputs={
            "kwargs": {
                "bk_biz_id": 3,
                "cluster_id": 59,
                "immute_domain": "m1.cyc30rs1.dba.db",
                "created_by": "admin",
            },
            "global_data": {},
        }
    )

    with patch.object(service, "log_info") as mock_log_info:
        assert service._execute(data, parent_data=None) is True

    assert "skip: cluster already absent" in mock_log_info.call_args.args[0]
    assert "id=59" in mock_log_info.call_args.args[0]
