# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent


class ClearMysqlMachineFlowTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow.Builder")
    def test_mysql_dts_uses_dts_script_and_skips_mysql_meta_cleanup(self, mock_builder):
        from backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow import ClearMysqlMachineFlow

        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        flow = ClearMysqlMachineFlow(
            root_id="root-dts-clear",
            data={
                "hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                "cluster_type": ClusterType.MySQLDTS.value,
                "dts_deploy_path": "/data/dts/dts-make-test",
            },
        )

        flow.run_flow()

        self.assertEqual(pipeline.add_act.call_count, 1)
        clear_call = pipeline.add_act.call_args
        self.assertEqual(clear_call.kwargs["act_component_code"], ClearMachineScriptComponent.code)
        script = clear_call.kwargs["kwargs"]["clear_machine_script"]
        self.assertIn('pkill -f "/data/dts/dts-make-test/bin/dm-worker"', script)
        self.assertIn('rm -rf "/data/dts/dts-make-test"', script)
        self.assertNotIn("/data/mysqldata", script)

    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow.Builder")
    def test_regular_mysql_keeps_mysql_cleanup(self, mock_builder):
        from backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow import ClearMysqlMachineFlow

        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        flow = ClearMysqlMachineFlow(
            root_id="root-mysql-clear",
            data={"hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}], "cluster_type": ClusterType.TenDBHA.value},
        )

        flow.run_flow()

        self.assertEqual(
            [item.kwargs["act_component_code"] for item in pipeline.add_act.call_args_list],
            [MySQLDBMetaComponent.code, ClearMachineScriptComponent.code],
        )
        self.assertEqual(
            pipeline.add_act.call_args_list[-1].kwargs["kwargs"],
            {"exec_ips": [{"ip": "127.0.0.2", "bk_cloud_id": 0}]},
        )

    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow.Builder")
    def test_mysql_dts_without_deploy_path_fails_closed(self, mock_builder):
        from backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow import ClearMysqlMachineFlow

        flow = ClearMysqlMachineFlow(
            root_id="root-dts-clear",
            data={
                "hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                "cluster_type": ClusterType.MySQLDTS.value,
            },
        )

        with self.assertRaisesRegex(ValueError, "dts_deploy_path"):
            flow.run_flow()
