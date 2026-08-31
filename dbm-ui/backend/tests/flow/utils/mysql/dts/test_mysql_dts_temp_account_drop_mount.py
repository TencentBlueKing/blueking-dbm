# -*- coding: utf-8 -*-
"""锁定 DTS 临时账号 DROP 挂载契约：总流程 dts-task-clean、migrate 末尾无硬挂、cleanup 无 drop。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.context import (
    MysqlDtsCleanupSubflowInput,
    MysqlDtsMigrateSubflowInput,
    MysqlDtsTaskCleanSubflowInput,
)
from backend.flow.utils.mysql.dts.migrate_credentials import DtsGrantTarget
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def _minimal_plan(**overrides):
    plan = SimpleNamespace(
        topology=MigrateTopology.ONE_TO_ONE.value,
        task_specs=[],
        dts_cluster_id=1,
        auto_deploy_dts=False,
        deploy_subflow_inp=None,
        dts_lifecycle="",
        worker_count_required=0,
        bk_biz_id=1,
        bk_cloud_id=0,
    )
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


class MysqlDtsTaskCleanSubflowTest(SimpleTestCase):
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.mysql_dts_delete_task_source_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.mysql_dts_drop_user_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.SubBuilder")
    def test_task_clean_mounts_drop_user_with_ignore_errors(self, mock_sub_builder, mock_drop_user, mock_delete):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow import (
            mysql_dts_task_clean_subflow,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        drop_sub = MagicMock()
        drop_sub.build_sub_process.return_value = "drop-sub"
        mock_drop_user.return_value = drop_sub
        delete_sub = MagicMock()
        delete_sub.build_sub_process.return_value = "delete-sub"
        mock_delete.return_value = delete_sub

        inp = MysqlDtsTaskCleanSubflowInput(
            root_id="root-clean",
            bk_biz_id=1,
            dts_user="dts_m_abc",
            grant_hosts=["127.0.0.3"],
            grant_targets=[{"bk_cloud_id": 0, "address": "127.0.0.2:3306", "cluster_id": 1}],
            ignore_errors=True,
            creator="tester",
            master_addr="127.0.0.4:8261",
            bk_cloud_id=0,
            task_names=["t1"],
            source_names=["s1"],
        )
        mysql_dts_task_clean_subflow(inp)

        drop_inp = mock_drop_user.call_args[0][0]
        self.assertEqual(drop_inp.dts_user, "dts_m_abc")
        self.assertTrue(drop_inp.ignore_errors)
        # DROP 账号必须排在 delete_task/source 之后，否则 DM 删 task 连下游会 1045
        self.assertEqual(sub.add_sub_pipeline.call_args_list, [call("delete-sub"), call("drop-sub")])
        sub.add_parallel_sub_pipeline.assert_not_called()


class MysqlDtsMigrateSubflowNoTailDropTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.mysql_dts_migrate_task_subflow")
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.build_dts_add_user_parallel_acts",
        return_value=[{"act_name": "add", "act_component_code": "x", "kwargs": {}}],
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.resolve_migrate_temp_account_for_pipeline",
        return_value=(
            "dts_u",
            "dts_p",
            ["127.0.0.3"],
            [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=100)],
        ),
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.resolve_master_addr_from_plan",
        return_value="127.0.0.4:8261",
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.mysql_dts_ensure_cluster_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.SubBuilder")
    def test_migrate_subflow_tail_has_no_drop_user(self, mock_sub_builder, mock_ensure, *_mocks):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow import mysql_dts_migrate_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mock_ensure.return_value.build_sub_process.return_value = MagicMock()

        inp = MysqlDtsMigrateSubflowInput(
            root_id="root-abc",
            bk_biz_id=1,
            ticket_id=18801,
            migrate_plan=_minimal_plan(),
            creator="tester",
        )
        mysql_dts_migrate_subflow(inp)

        for c in sub.add_sub_pipeline.call_args_list:
            kwargs = c.kwargs or {}
            args = c.args or ()
            name = str(kwargs.get("sub_flow") or (args[0] if args else ""))
            self.assertNotIn("drop", name.lower())
            self.assertNotIn("dts-task-clean", name.lower())


class MysqlDtsCleanupNoDropTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow.SubBuilder")
    def test_cleanup_subflow_has_no_drop_user(self, mock_sub_builder):
        from backend.flow.engine.bamboo.scene.mysql.dts import mysql_dts_cleanup_subflow as cleanup_mod
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow

        self.assertFalse(hasattr(cleanup_mod, "mysql_dts_drop_user_subflow"))
        self.assertFalse(hasattr(cleanup_mod, "_append_drop_temp_user_subflows"))

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        inp = MysqlDtsCleanupSubflowInput(
            root_id="root-destroy",
            dts_cluster_id=9,
            bk_biz_id=1,
            bk_cloud_id=0,
            master_addr="127.0.0.2:8261",
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0}],
            deploy_path="/data/dbbak/dts",
            creator="tester",
        )
        mysql_dts_cleanup_subflow(inp)

        act_names = [str(c.kwargs.get("act_name", "")) for c in sub.add_act.call_args_list]
        for name in act_names:
            self.assertNotIn("临时账号", name)
        sub.add_sub_pipeline.assert_not_called()

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow.SubBuilder")
    def test_cleanup_relay_act_before_optional_data_dir(self, mock_sub_builder):
        from django.utils.translation import gettext as _

        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mysql_dts_cleanup_subflow(
            MysqlDtsCleanupSubflowInput(
                root_id="root-destroy",
                dts_cluster_id=9,
                bk_biz_id=1,
                bk_cloud_id=0,
                master_addr="127.0.0.2:8261",
                master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0, "name": "dm-worker-1"}],
                deploy_path="/custom/dts",
                cluster_name="dts-prod",
                creator="tester",
                clean_data_dir=True,
            )
        )
        act_names = [str(c.kwargs.get("act_name", "")) for c in sub.add_act.call_args_list]
        relay_name = str(_("清理 DTS relay 与 exported_data"))
        data_dir_name = str(_("清理 DTS 部署目录"))
        self.assertIn(relay_name, act_names)
        self.assertIn(data_dir_name, act_names)
        self.assertLess(act_names.index(relay_name), act_names.index(data_dir_name))
        relay_act = next(c for c in sub.add_act.call_args_list if str(c.kwargs.get("act_name")) == relay_name)
        script = relay_act.kwargs["kwargs"]["shell_script"]
        self.assertIn("/custom/dts/dm-worker-1-data", script)
        self.assertIn("/custom/dts/exported_data", script)
        self.assertIn("/data/dts/dts-prod/exported_data", script)
        self.assertNotIn("/data/dbbak/", script)

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow.SubBuilder")
    def test_cleanup_relay_act_when_clean_data_dir_false(self, mock_sub_builder):
        from django.utils.translation import gettext as _

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        inp = MysqlDtsCleanupSubflowInput(
            root_id="root-destroy",
            dts_cluster_id=9,
            bk_biz_id=1,
            bk_cloud_id=0,
            master_addr="127.0.0.2:8261",
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0, "name": "dm-worker-1"}],
            deploy_path="/custom/dts",
            cluster_name="dts-prod",
            creator="tester",
            clean_data_dir=False,
        )
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow

        mysql_dts_cleanup_subflow(inp)
        act_names = [str(c.kwargs.get("act_name", "")) for c in sub.add_act.call_args_list]
        self.assertIn(str(_("清理 DTS relay 与 exported_data")), act_names)
        self.assertNotIn(str(_("清理 DTS 部署目录")), act_names)


class MysqlDtsCleanupClearMonitorTest(SimpleTestCase):
    def _inp(self, **overrides):
        data = {
            "root_id": "root-destroy",
            "dts_cluster_id": 9,
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "master_addr": "127.0.0.2:8261",
            "master_nodes": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            "worker_nodes": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
            "deploy_path": "/data/dbbak/dts",
            "creator": "tester",
        }
        data.update(overrides)
        return MysqlDtsCleanupSubflowInput(**data)

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow.SubBuilder")
    def test_clear_monitor_acts_before_unregister(self, mock_sub_builder):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mysql_dts_cleanup_subflow(self._inp())

        act_names = [str(c.kwargs.get("act_name", "")) for c in sub.add_act.call_args_list]
        clear_name = str(_("清理机器级别配置"))
        unreg_name = str(_("下线 DTS 集群元数据"))
        self.assertNotIn(str(_("下发db-actuator介质")), act_names)
        self.assertIn(clear_name, act_names)
        self.assertLess(act_names.index(clear_name), act_names.index(unreg_name))

        clear_act = next(c for c in sub.add_act.call_args_list if str(c.kwargs.get("act_name")) == clear_name)
        kwargs = clear_act.kwargs["kwargs"]
        self.assertEqual(kwargs["get_mysql_payload_func"], MysqlActPayload.get_clear_machine_crontab.__name__)
        self.assertEqual(kwargs["exec_ip"], ["127.0.0.2", "127.0.0.3"])

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow.SubBuilder")
    def test_no_hosts_skips_clear_monitor(self, mock_sub_builder):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mysql_dts_cleanup_subflow(self._inp(master_nodes=[], worker_nodes=[]))

        act_names = [str(c.kwargs.get("act_name", "")) for c in sub.add_act.call_args_list]
        self.assertNotIn(str(_("下发db-actuator介质")), act_names)
        self.assertNotIn(str(_("清理机器级别配置")), act_names)
        sub.add_parallel_acts.assert_not_called()


class OuterRunFlowDtsTaskCleanMountTest(SimpleTestCase):
    """总流程按行并行挂载：行内 migrate → dts-task-clean，凭证同源。"""

    _ROW_MOD = "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow"

    def _assert_run_flow_mount_order(self, flow_cls, module_path):
        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        plan = _minimal_plan()

        with patch(f"{module_path}.resolve_migrate_plans_from_ticket_data", return_value=[plan]), patch(
            f"{self._ROW_MOD}.resolve_migrate_temp_account_for_pipeline",
            return_value=("dts_m_shared", "pwd", ["127.0.0.3"], grant_targets),
        ), patch(f"{self._ROW_MOD}.resolve_master_addr_from_plan", return_value="127.0.0.4:8261"), patch(
            f"{self._ROW_MOD}.mysql_dts_migrate_subflow"
        ) as mock_migrate, patch(
            f"{self._ROW_MOD}.mysql_dts_task_clean_subflow"
        ) as mock_clean, patch(
            f"{self._ROW_MOD}.SubBuilder"
        ) as mock_sub_builder, patch(
            f"{module_path}.Builder"
        ) as mock_builder:
            pipeline = MagicMock()
            mock_builder.return_value = pipeline
            row_pipe = MagicMock()
            mock_sub_builder.return_value = row_pipe
            row_built = MagicMock(name="row-built")
            row_pipe.build_sub_process.return_value = row_built
            migrate_built = MagicMock(name="migrate-built")
            clean_built = MagicMock(name="clean-built")
            mock_migrate.return_value.build_sub_process.return_value = migrate_built
            mock_clean.return_value.build_sub_process.return_value = clean_built

            flow = flow_cls(root_id="root-outer", data={"bk_biz_id": 1, "ticket_id": 18801, "created_by": "t"})
            flow.run_flow()

            self.assertEqual(
                row_pipe.add_sub_pipeline.call_args_list,
                [call(migrate_built), call(clean_built)],
            )
            pipeline.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=[row_built])
            pipeline.add_sub_pipeline.assert_not_called()
            clean_sub_name = mock_clean.return_value.build_sub_process.call_args.kwargs.get("sub_name")
            self.assertEqual(str(clean_sub_name), str(_("dts-task-clean")))

            clean_inp = mock_clean.call_args[0][0]
            self.assertEqual(clean_inp.dts_user, "dts_m_shared")
            self.assertTrue(clean_inp.ignore_errors)

            migrate_inp = mock_migrate.call_args[0][0]
            self.assertEqual(migrate_inp.dts_user, "dts_m_shared")
            self.assertEqual(migrate_inp.dts_password, "pwd")
            pipeline.run_pipeline.assert_called_once()

    def test_mysql_to_mysql_run_flow_mounts_dts_task_clean(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate import MysqlToMysqlMigrateFlow

        self._assert_run_flow_mount_order(
            MysqlToMysqlMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate",
        )

    def test_ha_to_cluster_run_flow_mounts_dts_task_clean(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate import MysqlHaToClusterMigrateFlow

        self._assert_run_flow_mount_order(
            MysqlHaToClusterMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate",
        )
