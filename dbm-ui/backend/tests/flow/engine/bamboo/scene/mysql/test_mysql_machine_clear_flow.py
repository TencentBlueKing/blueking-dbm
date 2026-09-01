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

    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow.Builder")
    def test_mysql_dts_multi_path_parallel_clear_same_recycle_ticket(self, mock_builder):
        from backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow import ClearMysqlMachineFlow

        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        flow = ClearMysqlMachineFlow(
            root_id="root-dts-multi-path",
            data={
                "hosts": [
                    {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 1002},
                    {"ip": "127.0.0.3", "bk_cloud_id": 0, "bk_host_id": 1003},
                    {"ip": "127.0.0.4", "bk_cloud_id": 0, "bk_host_id": 1004},
                    {"ip": "127.0.0.5", "bk_cloud_id": 0, "bk_host_id": 1005},
                ],
                "cluster_type": ClusterType.MySQLDTS.value,
                "dts_deploy_path": "/data/dts/a",
                "dts_deploy_path_by_host": {
                    "1002": "/data/dts/a",
                    "1003": "/data/dts/a",
                    "1004": "/data/dts/b",
                    "1005": "/data/dts/b",
                },
            },
        )
        flow.run_flow()

        pipeline.add_act.assert_not_called()
        clear_call = pipeline.add_parallel_acts.call_args_list[0]
        acts = clear_call.kwargs.get("acts_list") or clear_call.args[0]
        self.assertEqual(len(acts), 2)
        scripts = [a["kwargs"]["clear_machine_script"] for a in acts]
        self.assertTrue(any("/data/dts/a" in s for s in scripts))
        self.assertTrue(any("/data/dts/b" in s for s in scripts))
        for script in scripts:
            self.assertGreaterEqual(script.count("pkill"), 1)
            self.assertIn("dm-worker", script)

    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow.Builder")
    def test_mysql_dts_same_path_by_host_stays_serial(self, mock_builder):
        from backend.flow.engine.bamboo.scene.mysql.mysql_machine_clear_flow import ClearMysqlMachineFlow

        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        flow = ClearMysqlMachineFlow(
            root_id="root-dts-one-path",
            data={
                "hosts": [
                    {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 1002},
                    {"ip": "127.0.0.3", "bk_cloud_id": 0, "bk_host_id": 1003},
                ],
                "cluster_type": ClusterType.MySQLDTS.value,
                "dts_deploy_path_by_host": {"1002": "/data/dts/a", "1003": "/data/dts/a"},
            },
        )
        flow.run_flow()
        clear_call = pipeline.add_act.call_args
        self.assertEqual(clear_call.kwargs["act_component_code"], ClearMachineScriptComponent.code)
        self.assertIn("/data/dts/a", clear_call.kwargs["kwargs"]["clear_machine_script"])
