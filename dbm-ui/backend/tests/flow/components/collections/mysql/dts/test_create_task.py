# -*- coding: utf-8 -*-
"""create_task：返回名必须与请求名一致。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.migrate.create_task import MysqlDtsCreateTaskService
from backend.flow.utils.mysql.dts.constants import FullLoadEngine
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskConfig


class MysqlDtsCreateTaskNameContractTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsCreateTaskService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(self, *, returned_name: str | None):
        task_spec = SimpleNamespace(
            task_name="mysql-dts-1-10-20",
            sources=[],
            dts_task_config=DtsTaskConfig(full_load_engine=FullLoadEngine.BUILTIN.value),
        )
        migrate_context = SimpleNamespace(
            master_addr="127.0.0.1:8261",
            bk_cloud_id=0,
            dts_user="dts_u",
            dts_password="pwd",
            dts_cluster_id=1,
            myloader_dirs={},
            myloader_path="",
            target_host="",
            target_port=0,
            target_cluster_type="",
        )
        trans_data = SimpleNamespace(migrate_context=migrate_context)
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "master_addr": "127.0.0.1:8261",
                "bk_cloud_id": 0,
                "task_spec": {"task_name": task_spec.task_name},
                "migrate_plan": {},
            },
            "trans_data": trans_data,
        }.get(key)
        data.outputs = MagicMock()

        resp = SimpleNamespace(
            task={"name": returned_name} if returned_name is not None else None,
            check_result={"ok": True},
        )
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.MySQLDTSApi"
        ) as mock_api, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.build_dts_task_request"
        ) as mock_build, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_migrate_plan_from_dict",
            return_value=SimpleNamespace(dts_cluster_id=1),
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_task_spec_from_dict",
            return_value=task_spec,
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task._apply_myloader_context_to_task_spec",
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.load_dts_cluster_name",
            return_value="dts-ut",
        ):
            mock_build.return_value = SimpleNamespace(
                task=SimpleNamespace(
                    target_config=SimpleNamespace(host="127.0.0.2", port=3306, cluster_type="tendbha")
                )
            )
            mock_api.create_task.return_value = resp
            ok = self._make_service()._execute(data, parent_data=None)
            return ok, data

    def test_same_name_succeeds(self):
        ok, data = self._run(returned_name="mysql-dts-1-10-20")
        self.assertTrue(ok)
        self.assertEqual(data.outputs.task_name, "mysql-dts-1-10-20")

    def test_missing_returned_name_succeeds_with_request_name(self):
        ok, data = self._run(returned_name=None)
        self.assertTrue(ok)
        self.assertEqual(data.outputs.task_name, "mysql-dts-1-10-20")

    def test_renamed_by_master_fails(self):
        ok, unused_data = self._run(returned_name="mysql-dts-renamed")
        self.assertFalse(ok)
