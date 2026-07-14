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

from backend.flow.plugins.components.collections.mongodb.mongo_update_version import MongoUpdateVersionService


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs

    def get_one_of_inputs(self, key):
        return self.inputs[key]


def _build_cluster(
    cluster_id=55,
    domain="dba-cycdevrs1.db",
    major_version="mongodb-6.0.27",
    storage_rows=None,
    proxy_rows=None,
):
    storage_rows = storage_rows or [
        {"port": 27001, "version": "mongodb-6.0.24", "machine__ip": "127.0.0.1"},
        {"port": 27002, "version": "mongodb-6.0.24", "machine__ip": "127.0.0.1"},
    ]
    proxy_rows = proxy_rows or []

    storage_qs = MagicMock()
    storage_qs.values.return_value = storage_rows
    storage_qs.update.return_value = len(storage_rows)

    proxy_qs = MagicMock()
    proxy_qs.values.return_value = proxy_rows
    proxy_qs.update.return_value = len(proxy_rows)

    cluster = SimpleNamespace(
        id=cluster_id,
        immute_domain=domain,
        major_version=major_version,
        cluster_type="MongoReplicaSet",
        storageinstance_set=storage_qs,
        proxyinstance_set=proxy_qs,
        save=MagicMock(),
    )
    return cluster


def _build_execute_data():
    return FakeData(
        inputs={
            "kwargs": {
                "cluster": {
                    "cluster_id_list": [55],
                    "bk_biz_id": 3,
                    "target_version": "mongodb-6.0.27",
                }
            },
            "global_data": {"job_root_id": "root-1"},
        }
    )


def test_snapshot_cluster_versions_collects_storage_and_proxy():
    cluster = _build_cluster(
        proxy_rows=[{"port": 27017, "version": "mongodb-6.0.24", "machine__ip": "127.0.0.2"}],
    )

    snapshot = MongoUpdateVersionService._snapshot_cluster_versions(cluster)

    assert snapshot == {
        "cluster_id": 55,
        "domain": "dba-cycdevrs1.db",
        "old_major_version": "mongodb-6.0.27",
        "instances": [
            {"type": "storage", "ip": "127.0.0.1", "port": 27001, "old_version": "mongodb-6.0.24"},
            {"type": "storage", "ip": "127.0.0.1", "port": 27002, "old_version": "mongodb-6.0.24"},
            {"type": "proxy", "ip": "127.0.0.2", "port": 27017, "old_version": "mongodb-6.0.24"},
        ],
    }


def test_log_cluster_version_updates_writes_before_after_lines():
    service = MongoUpdateVersionService()
    snapshot = {
        "cluster_id": 55,
        "domain": "dba-cycdevrs1.db",
        "old_major_version": "mongodb-6.0.27",
        "instances": [
            {"type": "storage", "ip": "127.0.0.1", "port": 27001, "old_version": "mongodb-6.0.24"},
        ],
    }

    with patch.object(service, "log_info") as mock_log_info:
        service._log_cluster_version_updates(snapshot, "mongodb-6.0.27", "mongodb-6.0.27")

    detail_log = mock_log_info.call_args.args[0]
    assert "[mongo version persist] cluster=dba-cycdevrs1.db (id=55)" in detail_log
    assert "major_version: mongodb-6.0.27 -> mongodb-6.0.27" in detail_log
    assert "storage 127.0.0.1:27001: mongodb-6.0.24 -> mongodb-6.0.27" in detail_log


@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.resolve_cluster_dbconf_level_value",
    return_value="dba-cycdevrs1",
)
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.migrate_mongodb_cluster_to_role")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.lookup_mongodb_package")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.Cluster.objects.filter")
def test_execute_logs_cluster_and_instance_version_updates(
    mock_cluster_filter, mock_lookup_package, mock_migrate_conf, _mock_level_value
):
    cluster = _build_cluster()
    queryset = MagicMock()
    queryset.exists.return_value = True
    queryset.__iter__ = MagicMock(return_value=iter([cluster]))
    mock_cluster_filter.return_value = queryset
    mock_lookup_package.return_value = SimpleNamespace(version="mongodb-6.0")
    mock_migrate_conf.return_value = {
        "migrated": True,
        "deleted_conf_files": ["Mongodb-6"],
        "target_conf_files": ["mongod.conf"],
    }

    service = MongoUpdateVersionService()
    data = _build_execute_data()

    with patch.object(
        service, "_resolve_metadata_versions", return_value={"cluster": "mongodb-6.0.27", "instance": "mongodb-6.0.27"}
    ):
        with patch.object(service, "log_info") as mock_log_info:
            assert service._execute(data, parent_data=None) is True

    mock_migrate_conf.assert_called_once()
    assert mock_log_info.call_count == 3
    detail_log = mock_log_info.call_args_list[1].args[0]
    summary_log = mock_log_info.call_args_list[2].args[0]
    conf_log = mock_log_info.call_args_list[0].args[0]

    assert "[mongo conf_file migrate]" in conf_log
    assert "[mongo version persist] cluster=dba-cycdevrs1.db (id=55)" in detail_log
    assert "major_version: mongodb-6.0.27 -> mongodb-6.0.27" in detail_log
    assert "storage 127.0.0.1:27001: mongodb-6.0.24 -> mongodb-6.0.27" in detail_log
    assert "storage 127.0.0.1:27002: mongodb-6.0.24 -> mongodb-6.0.27" in detail_log

    assert (
        "mongo clusters [dba-cycdevrs1.db] persist cluster_version=[mongodb-6.0.27] instance_version=[mongodb-6.0.27] done"
        in summary_log
    )
    assert "storage=2, proxy=0" in summary_log

    cluster.storageinstance_set.update.assert_called_once_with(version="mongodb-6.0.27")
    cluster.proxyinstance_set.update.assert_called_once_with(version="mongodb-6.0.27")
    assert cluster.major_version == "mongodb-6.0.27"
    cluster.save.assert_called_once_with(update_fields=["major_version"])


@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.resolve_cluster_dbconf_level_value",
    return_value="dba-cycdevrs1",
)
@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.migrate_mongodb_cluster_to_role",
    return_value={"migrated": False, "deleted_conf_files": [], "target_conf_files": []},
)
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.lookup_mongodb_package")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.Cluster.objects.filter")
def test_execute_marks_unchanged_instance_versions(
    mock_cluster_filter, mock_lookup_package, _mock_migrate_conf, _mock_level_value
):
    cluster = _build_cluster(
        storage_rows=[{"port": 27001, "version": "mongodb-6.0.27", "machine__ip": "127.0.0.1"}],
    )
    queryset = MagicMock()
    queryset.exists.return_value = True
    queryset.__iter__ = MagicMock(return_value=iter([cluster]))
    mock_cluster_filter.return_value = queryset
    mock_lookup_package.return_value = SimpleNamespace(version="mongodb-6.0")

    service = MongoUpdateVersionService()
    data = _build_execute_data()

    with patch.object(
        service, "_resolve_metadata_versions", return_value={"cluster": "mongodb-6.0.27", "instance": "mongodb-6.0.27"}
    ):
        with patch.object(service, "log_info") as mock_log_info:
            service._execute(data, parent_data=None)

    detail_log = mock_log_info.call_args_list[1].args[0]
    assert "storage 127.0.0.1:27001: mongodb-6.0.27 -> mongodb-6.0.27 (unchanged)" in detail_log


@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.lookup_mongodb_package",
    return_value=None,
)
@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.resolve_cluster_dbconf_level_value",
    return_value="dba-cycdevrs1",
)
@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.migrate_mongodb_cluster_to_role",
    return_value={"migrated": False, "deleted_conf_files": [], "target_conf_files": []},
)
@patch("backend.flow.plugins.components.collections.mongodb.mongo_update_version.Cluster.objects.filter")
def test_execute_raises_when_package_not_found(
    mock_cluster_filter, _mock_migrate_conf, _mock_level_value, _mock_lookup_package
):
    cluster = _build_cluster()
    queryset = MagicMock()
    queryset.exists.return_value = True
    queryset.__iter__ = MagicMock(return_value=iter([cluster]))
    mock_cluster_filter.return_value = queryset

    service = MongoUpdateVersionService()
    data = _build_execute_data()

    with patch.object(
        service, "_resolve_metadata_versions", return_value={"cluster": "mongodb-6.0.27", "instance": "mongodb-6.0.27"}
    ):
        with pytest.raises(ValueError, match="no mongodb package found"):
            service._execute(data, parent_data=None)


def test_resolve_conf_source_version_from_legacy_major():
    assert MongoUpdateVersionService._resolve_conf_source_version("Mongodb-6", "mongodb-7.0.14") == "mongodb-6.0"


@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.migrate_mongodb_cluster_to_role",
    return_value={"migrated": True, "deleted_conf_files": ["Mongodb-6"], "target_conf_files": ["mongod.conf"]},
)
@patch(
    "backend.flow.plugins.components.collections.mongodb.mongo_update_version.resolve_cluster_dbconf_level_value",
    return_value="dba-cycdevrs1",
)
def test_migrate_cluster_conf_to_role(mock_level_value, mock_migrate_role):
    cluster = _build_cluster(major_version="Mongodb-6")
    result = MongoUpdateVersionService._migrate_cluster_conf_on_version_update(
        cluster=cluster,
        bk_biz_id=3,
        old_major_version="Mongodb-6",
        target_cluster_version="mongodb-7.0",
    )
    mock_migrate_role.assert_called_once()
    assert result["migrated"] is True
