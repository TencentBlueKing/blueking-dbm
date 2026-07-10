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
            task_names=["t1"],
            source_names=["s1"],
        )
        mysql_dts_task_clean_subflow(inp)

        drop_inp = mock_drop_user.call_args[0][0]
        self.assertEqual(drop_inp.dts_user, "dts_m_abc")
        self.assertTrue(drop_inp.ignore_errors)
        # 二期：drop_user 与本单 delete_task/source 并行挂载
        sub.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=["drop-sub", "delete-sub"])
        sub.add_sub_pipeline.assert_not_called()


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

        act_names = [c.kwargs.get("act_name", "") for c in sub.add_act.call_args_list]
        for name in act_names:
            self.assertNotIn("临时账号", str(name))
        sub.add_sub_pipeline.assert_not_called()


class OuterRunFlowDtsTaskCleanMountTest(SimpleTestCase):
    def _assert_run_flow_mount_order(self, flow_cls, module_path):
        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        plan = _minimal_plan()

        with patch(f"{module_path}.resolve_migrate_plan_from_ticket_data", return_value=plan), patch(
            f"{module_path}.resolve_migrate_temp_account_for_pipeline",
            return_value=("dts_m_shared", "pwd", ["127.0.0.3"], grant_targets),
        ), patch(f"{module_path}.resolve_master_addr_from_plan", return_value="127.0.0.4:8261"), patch(
            f"{module_path}.mysql_dts_migrate_subflow"
        ) as mock_migrate, patch(
            f"{module_path}.mysql_dts_task_clean_subflow"
        ) as mock_clean, patch(
            f"{module_path}.Builder"
        ) as mock_builder:
            pipeline = MagicMock()
            mock_builder.return_value = pipeline
            migrate_built = MagicMock(name="migrate-built")
            clean_built = MagicMock(name="clean-built")
            mock_migrate.return_value.build_sub_process.return_value = migrate_built
            mock_clean.return_value.build_sub_process.return_value = clean_built

            flow = flow_cls(root_id="root-outer", data={"bk_biz_id": 1, "ticket_id": 18801, "created_by": "t"})
            flow.run_flow()

            # migrate → dts-task-clean → run_pipeline
            self.assertEqual(
                pipeline.add_sub_pipeline.call_args_list,
                [call(migrate_built), call(clean_built)],
            )
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
