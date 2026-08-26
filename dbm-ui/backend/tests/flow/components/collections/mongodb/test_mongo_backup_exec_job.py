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
import base64
import inspect
import json
from unittest.mock import MagicMock, patch

from backend.flow.engine.bamboo.scene.mongodb.mongodb_backup import MongoBackupFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.backup import BackupSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job import (
    MongoBackupExecJobComponent,
    MongoBackupExecService,
    MongoBackupFileSerializer,
)


class FakeOutputs:
    """兼容 pipeline data.outputs.xxx = value 与 get_one_of_outputs 读取。"""

    def __init__(self, initial=None):
        object.__setattr__(self, "_data", dict(initial or {}))

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __setattr__(self, key, value):
        if key == "_data":
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value


class FakeData:
    def __init__(self, inputs=None, outputs=None):
        self.inputs = inputs or {}
        self.outputs = FakeOutputs(outputs)

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)

    def get_one_of_outputs(self, key):
        return self.outputs.get(key)


def _backup_ctx(**overrides):
    ctx = {
        "cluster_domain": "m1.demo.db",
        "set_name": "pl",
        "instance": "127.0.0.1:27001",
        "file_name": "mongodump-127.0.0.1-27001-1710000000.tar.zstd",
        "file_path": "/data/dbbak/billdump/mongodump-127.0.0.1-27001-1710000000.tar.zstd",
        "file_size": 1024,
        "bs_taskid": "task-1001",
        "bs_tag": "DBFILE1M",
    }
    ctx.update(overrides)
    return ctx


def _encode_ctx(ctx: dict) -> str:
    return base64.b64encode(json.dumps(ctx).encode("utf-8")).decode("utf-8")


def _build_service():
    service = MongoBackupExecService()
    service._runtime_attrs = {"root_pipeline_id": "root-backup-1", "id": "node-1", "version": "v1"}
    service.log_info = MagicMock()
    service.log_warning = MagicMock()
    return service


def _job_data(ctx_payload: str):
    return FakeData(
        inputs={"kwargs": {"bk_cloud_id": 0, "exec_ip": "127.0.0.1"}},
        outputs={
            "ext_result": {"result": True, "data": {"job_instance_id": 9001}},
            "exec_ips": ["127.0.0.1"],
            "job_execute": True,
        },
    )


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_ip_log")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_status")
def test_parse_backup_ctx_from_base64_job_log(mock_status, mock_log):
    ctx = _backup_ctx()
    mock_status.return_value = {
        "result": True,
        "data": {"step_instance_list": [{"step_instance_id": 8001}]},
    }
    mock_log.return_value = {
        "result": True,
        "data": {"log_content": f"backup done\n<ctx>{_encode_ctx(ctx)}</ctx>\nheartbeat"},
    }

    service = _build_service()
    row = service._parse_backup_ctx_from_job(_job_data(""))

    assert row["bs_taskid"] == "task-1001"
    assert row["file_name"] == ctx["file_name"]
    assert row["instance"] == "127.0.0.1:27001"
    assert row["file_size"] == 1024
    assert row["cluster_domain"] == "m1.demo.db"
    assert row["set_name"] == "pl"


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_ip_log")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_status")
def test_parse_backup_ctx_from_raw_json_job_log(mock_status, mock_log):
    ctx = _backup_ctx(bs_taskid="task-raw")
    mock_status.return_value = {
        "result": True,
        "data": {"step_instance_list": [{"step_instance_id": 8001}]},
    }
    mock_log.return_value = {
        "result": True,
        "data": {"log_content": f"<ctx>{json.dumps(ctx)}</ctx>"},
    }

    service = _build_service()
    row = service._parse_backup_ctx_from_job(_job_data(""))

    assert row["bs_taskid"] == "task-raw"
    assert row["file_name"] == ctx["file_name"]


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_ip_log")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_status")
def test_parse_backup_ctx_missing_ctx_returns_empty(mock_status, mock_log):
    mock_status.return_value = {
        "result": True,
        "data": {"step_instance_list": [{"step_instance_id": 8001}]},
    }
    mock_log.return_value = {"result": True, "data": {"log_content": "no ctx here"}}

    service = _build_service()
    assert service._parse_backup_ctx_from_job(_job_data("")) == {}


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_ip_log")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_status")
def test_parse_backup_ctx_missing_bs_taskid_returns_empty(mock_status, mock_log):
    ctx = _backup_ctx(bs_taskid="")
    mock_status.return_value = {
        "result": True,
        "data": {"step_instance_list": [{"step_instance_id": 8001}]},
    }
    mock_log.return_value = {
        "result": True,
        "data": {"log_content": f"<ctx>{_encode_ctx(ctx)}</ctx>"},
    }

    service = _build_service()
    assert service._parse_backup_ctx_from_job(_job_data("")) == {}


def test_mongo_backup_file_serializer_fields():
    assert MongoBackupFileSerializer.table_name == "mongo_backup_files"
    assert MongoBackupFileSerializer.table_primary_key == "bs_taskid"
    slz = MongoBackupFileSerializer(
        data={
            "cluster_domain": "m1.demo.db",
            "set_name": "pl",
            "instance": "127.0.0.1:27001",
            "file_name": "a.tar.zstd",
            "file_size": 10,
            "file_path": "/data/a.tar.zstd",
            "bs_taskid": "t1",
        }
    )
    assert slz.is_valid(), slz.errors


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.FlowOutputHandler")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.Flow.objects.filter")
def test_write_backup_flow_output_skips_without_flow(mock_filter, mock_handler):
    mock_filter.return_value.exists.return_value = False
    service = _build_service()
    service._write_backup_flow_output(_job_data(""))
    mock_handler.assert_not_called()
    service.log_info.assert_called()


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.FlowOutputHandler")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.Flow.objects.filter")
def test_write_backup_flow_output_inserts_row(mock_filter, mock_handler):
    mock_filter.return_value.exists.return_value = True
    handler = mock_handler.return_value
    service = _build_service()
    row = _backup_ctx()
    with patch.object(service, "_parse_backup_ctx_from_job", return_value=row):
        service._write_backup_flow_output(_job_data(""))

    mock_handler.assert_called_once_with(MongoBackupFileSerializer)
    handler.insert_data.assert_called_once_with("root-backup-1", row)


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.FlowOutputHandler")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.Flow.objects.filter")
def test_write_backup_flow_output_empty_row_skips_insert(mock_filter, mock_handler):
    mock_filter.return_value.exists.return_value = True
    service = _build_service()
    with patch.object(service, "_parse_backup_ctx_from_job", return_value={}):
        service._write_backup_flow_output(_job_data(""))
    mock_handler.assert_not_called()
    service.log_warning.assert_called()


def test_schedule_writes_only_when_job_execute_true():
    service = _build_service()
    data = FakeData(outputs={"job_execute": True})
    with patch.object(ExecJobComponent2.bound_service, "_schedule", return_value=True) as mock_super:
        with patch.object(service, "_write_backup_flow_output") as mock_write:
            assert service._schedule(data, None) is True
    mock_super.assert_called_once()
    mock_write.assert_called_once_with(data)
    assert data.get_one_of_outputs("backup_flow_output_written") is True


def test_schedule_skips_write_while_polling():
    service = _build_service()
    data = FakeData(outputs={})  # job_execute not set yet
    with patch.object(ExecJobComponent2.bound_service, "_schedule", return_value=True):
        with patch.object(service, "_write_backup_flow_output") as mock_write:
            assert service._schedule(data, None) is True
    mock_write.assert_not_called()


def test_schedule_failure_does_not_write():
    service = _build_service()
    data = FakeData(outputs={"job_execute": False})
    with patch.object(ExecJobComponent2.bound_service, "_schedule", return_value=False):
        with patch.object(service, "_write_backup_flow_output") as mock_write:
            assert service._schedule(data, None) is False
    mock_write.assert_not_called()


def test_schedule_skips_write_when_already_written():
    service = _build_service()
    data = FakeData(outputs={"job_execute": True, "backup_flow_output_written": True})
    with patch.object(ExecJobComponent2.bound_service, "_schedule", return_value=True):
        with patch.object(service, "_write_backup_flow_output") as mock_write:
            assert service._schedule(data, None) is True
    mock_write.assert_not_called()


@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_ip_log")
@patch("backend.flow.plugins.components.collections.mongodb.mongo_backup_exec_job.JobApi.get_job_instance_status")
def test_parse_backup_ctx_empty_step_list_returns_empty(mock_status, mock_log):
    mock_status.return_value = {"result": True, "data": {"step_instance_list": []}}
    service = _build_service()
    assert service._parse_backup_ctx_from_job(_job_data("")) == {}
    mock_log.assert_not_called()


def test_backup_flow_uses_mongo_backup_exec_component():
    assert MongoBackupExecJobComponent.code == "MongoBackupExecJobComponent"
    assert "MongoDB备份" in str(MongoBackupExecJobComponent.name)
    assert MongoBackupExecJobComponent.name != __name__
    backup_src = inspect.getsource(BackupSubTask.process_cluster)
    flow_src = inspect.getsource(MongoBackupFlow.backup_cluster)
    assert "MongoBackupExecJobComponent" in backup_src
    assert "MongoBackupExecJobComponent" in flow_src
