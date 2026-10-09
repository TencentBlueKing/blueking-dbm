# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.mysql_exercise_binlog_query import (
    MysqlExerciseBinlogDownloadService,
    MysqlExerciseBinlogQueryService,
)
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLRollbackExerciseContext


class FakeOutputs(SimpleNamespace):
    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)


class FakeData:
    def __init__(self, inputs=None):
        self.inputs = inputs or {}
        self.outputs = FakeOutputs()

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _kwargs(**overrides):
    data = {
        "cluster_id": 1,
        "backup_time": "2026-09-15T10:00:00+08:00",
        "rollback_time": "2026-09-15T11:05:00+08:00",
        "backup_info": {
            "backup_id": "b1",
            "mysql_role": "master",
            "binlog_info": {
                "show_master_status": {
                    "master_host": "127.0.0.2",
                    "master_port": 20000,
                    "binlog_file": "binlog.000001",
                    "binlog_pos": 4,
                }
            },
        },
    }
    data.update(overrides)
    return data


class MysqlExerciseBinlogQueryServiceTest(SimpleTestCase):
    def _run(self, handler_result=None, handler_exc=None, kwargs=None):
        trans_data = MySQLRollbackExerciseContext()
        data = FakeData({"kwargs": kwargs or _kwargs(), "trans_data": trans_data, "global_data": {}})
        service = MysqlExerciseBinlogQueryService()
        handler = MagicMock()
        if handler_exc:
            handler.get_binlog_for_rollback.side_effect = handler_exc
        else:
            handler.get_binlog_for_rollback.return_value = handler_result or {}
        with patch(
            "backend.flow.plugins.components.collections.mysql.mysql_exercise_binlog_query.MySQLBackupHandler",
            return_value=handler,
        ):
            ok = service._execute(data, {})
        return ok, data, trans_data, handler

    def test_success_writes_context_and_code_zero(self):
        ok, data, trans_data, handler = self._run(
            handler_result={
                "binlog_task_ids": ["tid-1", "tid-2"],
                "binlog_files_list": ["binlog.000001", "binlog.000002"],
                "binlog_start_file": "binlog.000001",
                "binlog_start_pos": 4,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(data.outputs.binlog_query_code, 0)
        self.assertEqual(trans_data.binlog_task_ids, ["tid-1", "tid-2"])
        self.assertEqual(trans_data.binlog_files_list, ["binlog.000001", "binlog.000002"])
        self.assertEqual(trans_data.binlog_start_file, "binlog.000001")
        self.assertEqual(trans_data.binlog_start_pos, 4)
        handler.get_binlog_for_rollback.assert_called_once()

    def test_query_binlog_error_returns_code_one_without_raise(self):
        ok, data, trans_data, handler = self._run(
            handler_result={"query_binlog_error": "backup missing show_master_status"}
        )
        handler.get_binlog_for_rollback.assert_called_once()
        self.assertFalse(ok)
        self.assertEqual(data.outputs.binlog_query_code, 1)
        self.assertIn("show_master_status", trans_data.rollback_error_info["error_logs"])

    def test_missing_binlog_files_returns_code_one(self):
        ok, data, trans_data, handler = self._run(
            handler_result={
                "binlog_task_ids": ["tid-1", "tid-3"],
                "binlog_files_list": ["binlog.000001", "binlog.000003"],
                "binlog_start_file": "binlog.000001",
                "binlog_start_pos": 4,
            }
        )
        handler.get_binlog_for_rollback.assert_called_once()
        self.assertFalse(ok)
        self.assertEqual(data.outputs.binlog_query_code, 1)
        self.assertIn("binlog.000002", trans_data.rollback_error_info["error_logs"])

    def test_handler_exception_returns_code_one_without_raise(self):
        ok, data, trans_data, handler = self._run(handler_exc=RuntimeError("db down"))
        self.assertFalse(ok)
        self.assertEqual(data.outputs.binlog_query_code, 1)
        self.assertIn("db down", trans_data.rollback_error_info["error_logs"])
        handler.get_binlog_for_rollback.assert_called_once()

    def test_logs_apply_and_query_window(self):
        trans_data = MySQLRollbackExerciseContext()
        data = FakeData({"kwargs": _kwargs(), "trans_data": trans_data, "global_data": {}})
        service = MysqlExerciseBinlogQueryService()
        service.log_info = MagicMock()
        handler = MagicMock()
        handler.query = "SELECT ... start_time >= ..."
        handler.get_binlog_for_rollback.return_value = {
            "binlog_task_ids": ["tid-1"],
            "binlog_files_list": ["binlog.000001"],
            "binlog_start_file": "binlog.000001",
            "binlog_start_pos": 4,
        }
        with patch(
            "backend.flow.plugins.components.collections.mysql.mysql_exercise_binlog_query.MySQLBackupHandler",
            return_value=handler,
        ):
            self.assertTrue(service._execute(data, {}))
        texts = [str(c.args[0]) for c in service.log_info.call_args_list]
        joined = " ".join(texts)
        self.assertTrue(any("实际查询窗=" in t for t in texts))
        self.assertIn("2026-09-15T10:00:00", joined)
        self.assertIn("2026-09-15T11:05:00", joined)
        self.assertIn("2026-09-15T09:30:00", joined)
        self.assertIn("2026-09-15T11:35:00", joined)
        self.assertTrue(any("binlog.000001" in t and "起始文件" in t for t in texts))


class MysqlExerciseBinlogDownloadServiceTest(SimpleTestCase):
    def test_schedule_sets_download_code_on_terminal_not_poll(self):
        trans_data = MySQLRollbackExerciseContext()
        data = FakeData({"kwargs": {}, "trans_data": trans_data})
        service = MysqlExerciseBinlogDownloadService()
        parent = (
            "backend.flow.plugins.components.collections.mysql."
            "mysql_exercise_binlog_query.MySQLDownloadBackupfile._schedule"
        )
        with patch(parent, return_value=None):
            self.assertIsNone(service._schedule(data, {}))
            self.assertFalse(hasattr(data.outputs, "binlog_download_code"))
        with patch(parent, return_value=True):
            self.assertTrue(service._schedule(data, {}))
            self.assertEqual(data.outputs.binlog_download_code, 0)
        with patch(parent, return_value=False):
            self.assertFalse(service._schedule(data, {}))
            self.assertEqual(data.outputs.binlog_download_code, 1)
