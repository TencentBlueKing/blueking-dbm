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
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.plugins.components.collections.mysql.exec_actuator_script_with_bk_job_record import (
    ExecuteDBActuatorScriptWithBkJobRecordService,
)
from backend.flow.utils import sql_file_exec_duration_recorder as recorder


def _ctx_log(sql_file="foo.sql", db_name="db1", duration=3, extra=None):
    item = {"sql_file": sql_file, "db_name": db_name, "duration": duration, "success": True}
    if extra:
        item.update(extra)
    inner = json.dumps({"3306": [item]})
    return f"prefix <ctx>{inner}</ctx> suffix"


def _fetch_ok(log_content=None):
    content = log_content if log_content is not None else _ctx_log()

    def _fetch(_ip_dict):
        return {"result": True, "data": {"log_content": content}}

    return _fetch


class FakeData:
    def __init__(self, inputs=None, outputs=None):
        self._inputs = inputs or {}
        self._outputs = outputs or {}

    def get_one_of_inputs(self, key):
        return self._inputs.get(key)

    def get_one_of_outputs(self, key):
        return self._outputs.get(key)


def _ok_data(uid=100, path="mysql/sqlfile/123", cluster_id=9):
    return FakeData(
        inputs={
            "global_data": {"uid": uid, "path": path},
            "kwargs": {
                "cluster": {"cluster_id": cluster_id},
                "root_id": "r" * 33,
                "bk_cloud_id": 0,
            },
        },
        outputs={
            "exec_ips": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "ext_result": {"result": True, "data": {"job_instance_id": 1, "step_instance_id": 2}},
            "job_execute": True,
        },
    )


def _make_service():
    svc = object.__new__(ExecuteDBActuatorScriptWithBkJobRecordService)
    svc.log_exception = MagicMock()
    return svc


class TestSqlFileExecDurationRecorder(SimpleTestCase):
    def test_parse_ctx_includes_db_name(self):
        rows = recorder.parse_sql_file_exec_ctx(_ctx_log(db_name="db1"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["db_name"], "db1")
        self.assertEqual(rows[0]["sql_file"], "foo.sql")
        self.assertEqual(rows[0]["duration_sec"], 3)
        self.assertEqual(rows[0]["port"], 3306)
        self.assertTrue(rows[0]["success"])

    def test_join_sql_file_path_object_path(self):
        self.assertEqual(
            recorder.join_sql_file_path("mysql/sqlfile/123", "foo.sql"),
            "mysql/sqlfile/123/foo.sql",
        )
        self.assertEqual(
            recorder.join_sql_file_path("/mysql/sqlfile/123/", "foo.sql"),
            "mysql/sqlfile/123/foo.sql",
        )
        self.assertEqual(recorder.join_sql_file_path("", "foo.sql"), "")
        self.assertEqual(recorder.join_sql_file_path("mysql/sqlfile/123", ""), "")

    def test_collect_joins_bkrepo_object_path(self):
        objs = recorder._collect_duration_objs(
            fetch_ip_log=_fetch_ok(),
            ip_dicts=[{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            ticket_id=100,
            cluster_id=9,
            cluster_domain="gamedb.example.db",
            root_id="r" * 33,
            repo_dir="mysql/sqlfile/123",
        )
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].sql_file_path, "mysql/sqlfile/123/foo.sql")
        self.assertEqual(objs[0].ticket_id, 100)
        self.assertEqual(objs[0].cluster_id, 9)
        self.assertEqual(objs[0].db_name, "db1")
        self.assertEqual(objs[0].sql_file, "foo.sql")
        self.assertEqual(objs[0].duration_sec, 3)
        self.assertEqual(objs[0].ip, "127.0.0.1")
        self.assertEqual(objs[0].port, 3306)

    @patch.object(recorder, "_collect_duration_objs")
    @patch.object(recorder, "_resolve_cluster_domain", return_value="gamedb.example.db")
    def test_persist_bulk_create_ignore_conflicts(self, _mock_domain, mock_collect):
        mock_collect.return_value = [MagicMock()]
        with patch.object(recorder.MysqlSqlFileExecDuration.objects.__class__, "bulk_create") as mock_bulk:
            mock_bulk.return_value = []
            count = recorder.record_sql_file_exec_durations(data=_ok_data(), fetch_ip_log=_fetch_ok())
        self.assertEqual(count, 1)
        mock_bulk.assert_called_once()
        self.assertTrue(mock_bulk.call_args.kwargs.get("ignore_conflicts"))

    @patch.object(recorder.MysqlSqlFileExecDuration.objects, "bulk_create")
    def test_missing_ticket_id_skips(self, mock_bulk):
        data = _ok_data()
        data._inputs["global_data"]["uid"] = None
        count = recorder.record_sql_file_exec_durations(data=data, fetch_ip_log=_fetch_ok())
        self.assertEqual(count, 0)
        mock_bulk.assert_not_called()

    @patch.object(recorder.MysqlSqlFileExecDuration.objects, "bulk_create")
    def test_missing_cluster_id_skips(self, mock_bulk):
        data = _ok_data()
        data._inputs["kwargs"] = {"root_id": "r" * 33, "bk_cloud_id": 0}
        count = recorder.record_sql_file_exec_durations(data=data, fetch_ip_log=_fetch_ok())
        self.assertEqual(count, 0)
        mock_bulk.assert_not_called()

    @patch.object(BkJobService, "_schedule", return_value=True)
    def test_schedule_persist_exception_does_not_fail_node(self, _mock_super):
        svc = _make_service()
        data = _ok_data()
        with patch(
            "backend.flow.plugins.components.collections.mysql.exec_actuator_script_with_bk_job_record."
            "record_sql_file_exec_durations",
            side_effect=RuntimeError("db down"),
        ):
            self.assertTrue(svc._schedule(data, None))
        svc.log_exception.assert_called_once()

    @patch.object(BkJobService, "_schedule", return_value=False)
    def test_schedule_job_fail_does_not_record(self, _mock_super):
        svc = _make_service()
        data = _ok_data()
        with patch(
            "backend.flow.plugins.components.collections.mysql.exec_actuator_script_with_bk_job_record."
            "record_sql_file_exec_durations"
        ) as mock_record:
            self.assertFalse(svc._schedule(data, None))
            mock_record.assert_not_called()

    @patch.object(BkJobService, "_schedule", return_value=True)
    def test_schedule_skips_when_job_execute_not_true(self, _mock_super):
        svc = _make_service()
        data = _ok_data()
        data._outputs["job_execute"] = False
        with patch(
            "backend.flow.plugins.components.collections.mysql.exec_actuator_script_with_bk_job_record."
            "record_sql_file_exec_durations"
        ) as mock_record:
            self.assertTrue(svc._schedule(data, None))
            mock_record.assert_not_called()
