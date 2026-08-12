# -*- coding: utf-8 -*-
"""本单维度 delete_task → delete_source 组件单测。"""
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source import (
    MysqlDtsDeleteTaskSourceService,
)


class MysqlDtsDeleteTaskSourceServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsDeleteTaskSourceService()
        service.log_info = MagicMock()
        service.log_warning = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(self, kwargs, *, trans_data=None):
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": kwargs,
            "trans_data": trans_data,
        }.get(key)
        return self._make_service()._execute(data, parent_data=None)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_deletes_tasks_then_sources_in_order(self, mock_api):
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1", "s2"],
                "ignore_errors": True,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(
            mock_api.mock_calls,
            [
                call.delete_task("127.0.0.4:8261", "t1", force=True, bk_cloud_id=0),
                call.delete_task("127.0.0.4:8261", "t2", force=True, bk_cloud_id=0),
                call.delete_source("127.0.0.4:8261", "s1", force=True, bk_cloud_id=0),
                call.delete_source("127.0.0.4:8261", "s2", force=True, bk_cloud_id=0),
            ],
        )
        mock_api.list_tasks.assert_not_called()
        mock_api.list_sources.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_ignore_errors_partial_failure_still_succeeds(self, mock_api):
        mock_api.delete_task.side_effect = [None, RuntimeError("gone")]
        mock_api.delete_source.side_effect = RuntimeError("missing")
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1"],
                "ignore_errors": True,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(mock_api.delete_task.call_count, 2)
        self.assertEqual(mock_api.delete_source.call_count, 1)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_empty_names_skips(self, mock_api):
        self.assertTrue(
            self._run({"master_addr": "127.0.0.4:8261", "bk_cloud_id": 0, "task_names": [], "source_names": []})
        )
        self.assertTrue(self._run({"master_addr": "", "task_names": [], "source_names": []}))
        mock_api.delete_task.assert_not_called()
        mock_api.delete_source.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_empty_master_with_names_fails(self, mock_api):
        self.assertFalse(
            self._run({"master_addr": "", "bk_cloud_id": 0, "task_names": ["t1"], "source_names": ["s1"]})
        )
        # ignore_errors 也不能把「无 Master」当成成功
        self.assertFalse(
            self._run(
                {
                    "master_addr": "",
                    "bk_cloud_id": 0,
                    "task_names": ["t1"],
                    "source_names": [],
                    "ignore_errors": True,
                }
            )
        )
        mock_api.delete_task.assert_not_called()
        mock_api.delete_source.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_strict_mode_partial_failure_returns_false(self, mock_api):
        mock_api.delete_task.side_effect = [None, RuntimeError("gone")]
        mock_api.delete_source.return_value = None
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1"],
                # 默认 ignore_errors=False
            }
        )
        self.assertFalse(ok)
        self.assertEqual(mock_api.delete_task.call_count, 2)
        self.assertEqual(mock_api.delete_source.call_count, 1)
