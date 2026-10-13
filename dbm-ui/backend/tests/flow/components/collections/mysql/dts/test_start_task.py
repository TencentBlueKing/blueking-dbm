# -*- coding: utf-8 -*-
"""start_task：启动前打印可复制的 dmctl 只读命令。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.migrate.start_task import MysqlDtsStartTaskService


class MysqlDtsStartTaskDmctlLogTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsStartTaskService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(self, *, registered_source_names=None, source_name_list=None):
        migrate_context = SimpleNamespace(
            master_addr="127.0.0.1:8261",
            bk_cloud_id=0,
            registered_source_names=registered_source_names or [],
            target_host="127.0.0.2",
            target_port=20000,
            target_cluster_type="tendbha",
        )
        trans_data = SimpleNamespace(migrate_context=migrate_context)
        kwargs = {
            "master_addr": "127.0.0.1:8261",
            "bk_cloud_id": 0,
            "task_name": "mysql-dts-1-10-20",
        }
        if source_name_list is not None:
            kwargs["source_name_list"] = source_name_list
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": kwargs,
            "trans_data": trans_data,
        }.get(key)
        service = self._make_service()
        with patch("backend.flow.plugins.components.collections.mysql.dts.migrate.start_task.MySQLDTSApi") as mock_api:
            ok = service._execute(data, parent_data=None)
        logged = [call.args[0] for call in service.log_info.call_args_list]
        return ok, logged, mock_api

    def test_logs_readonly_commands_with_registered_source(self):
        ok, logged, mock_api = self._run(registered_source_names=["source-10-abc"])
        self.assertTrue(ok)
        joined = "\n".join(logged)
        self.assertIn("dmctl --master-addr 127.0.0.1:8261 query-status mysql-dts-1-10-20", joined)
        self.assertIn("dmctl --master-addr 127.0.0.1:8261 operate-source show", joined)
        self.assertIn("dmctl --master-addr 127.0.0.1:8261 get-config task mysql-dts-1-10-20", joined)
        self.assertIn("dmctl --master-addr 127.0.0.1:8261 get-config source source-10-abc", joined)
        self.assertNotIn("pause-task", joined)
        self.assertNotIn("stop-task", joined)
        self.assertNotIn("resume-task", joined)
        mock_api.start_task.assert_called_once()
        self.assertIsNone(mock_api.start_task.call_args.args[2])

    def test_omits_source_command_when_name_missing(self):
        ok, logged, unused_api = self._run()
        self.assertTrue(ok)
        joined = "\n".join(logged)
        self.assertIn("query-status mysql-dts-1-10-20", joined)
        self.assertNotIn("get-config source", joined)

    def test_falls_back_to_kwargs_source_name_list(self):
        ok, logged, mock_api = self._run(source_name_list=["source-from-kwargs"])
        self.assertTrue(ok)
        self.assertIn(
            "dmctl --master-addr 127.0.0.1:8261 get-config source source-from-kwargs",
            "\n".join(logged),
        )
        self.assertEqual(mock_api.start_task.call_args.args[2].source_name_list, ["source-from-kwargs"])

    def test_registered_name_wins_over_kwargs(self):
        ok, logged, unused_api = self._run(
            registered_source_names=["source-registered"],
            source_name_list=["source-from-kwargs"],
        )
        self.assertTrue(ok)
        joined = "\n".join(logged)
        self.assertIn("get-config source source-registered", joined)
        self.assertNotIn("get-config source source-from-kwargs", joined)
