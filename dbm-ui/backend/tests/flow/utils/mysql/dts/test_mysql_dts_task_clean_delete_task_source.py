# -*- coding: utf-8 -*-
"""锁定 dts-task-clean：并行挂载、本单名称组装、不引用 DESTROY 全量扫删。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.context import MysqlDtsTaskCleanSubflowInput
from backend.flow.utils.mysql.dts.migrate_credentials import DtsGrantTarget
from backend.flow.utils.mysql.dts.migrate_helper import build_ticket_dts_clean_names
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsTaskConfig,
    DtsTaskSpec,
    SourceSpec,
    SyncScope,
    build_migrate_plan,
)


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


class BuildTicketDtsCleanNamesTest(SimpleTestCase):
    def test_one_to_one_names_match_plan(self):
        plan = build_migrate_plan(
            {
                "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": "mysql-dts-t1",
                    "src_info": {"cluster_id": 1},
                    "dst_info": {"cluster_id": 2},
                },
            }
        )
        task_names, source_names = build_ticket_dts_clean_names(plan)
        self.assertEqual(task_names, ["mysql-dts-t1"])
        self.assertEqual(source_names, [plan.task_specs[0].sources[0].source_name])

    def test_many_to_one_collects_all_sources(self):
        plan = build_migrate_plan(
            {
                "migrate_topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "task_name": "mysql-dts-m2o",
                    "src_infos": [{"cluster_id": 1}, {"cluster_id": 2}],
                    "dst_info": {"cluster_id": 10},
                },
            }
        )
        task_names, source_names = build_ticket_dts_clean_names(plan)
        self.assertEqual(task_names, ["mysql-dts-m2o"])
        self.assertEqual(len(source_names), 2)
        self.assertEqual(set(source_names), {s.source_name for s in plan.task_specs[0].sources})

    def test_one_to_many_collects_all_tasks(self):
        plan = build_migrate_plan(
            {
                "migrate_topology": MigrateTopology.ONE_TO_MANY.value,
                "one_to_many": {
                    "src_info": {"cluster_id": 1},
                    "dst_infos": [
                        {"cluster_id": 2, "task_name": "mysql-dts-o2m-a"},
                        {"cluster_id": 3, "task_name": "mysql-dts-o2m-b"},
                    ],
                },
            }
        )
        task_names, source_names = build_ticket_dts_clean_names(plan)
        self.assertEqual(task_names, ["mysql-dts-o2m-a", "mysql-dts-o2m-b"])
        # ONE_TO_MANY：各 task 各自生成唯一 source_name，并集即本单全部 source
        self.assertEqual(len(source_names), 2)
        self.assertEqual(len(source_names), len(set(source_names)))

    def test_dedupe_preserves_order(self):
        src = SourceSpec(cluster_id=1, source_name="src-a", sync_scope=SyncScope(do_dbs=["db"]))
        plan = _minimal_plan(
            task_specs=[
                DtsTaskSpec(task_name="t1", target_cluster_id=2, sources=[src], dts_task_config=DtsTaskConfig()),
                DtsTaskSpec(task_name="t1", target_cluster_id=3, sources=[src], dts_task_config=DtsTaskConfig()),
            ]
        )
        task_names, source_names = build_ticket_dts_clean_names(plan)
        self.assertEqual(task_names, ["t1"])
        self.assertEqual(source_names, ["src-a"])


class MysqlDtsTaskCleanParallelMountTest(SimpleTestCase):
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.mysql_dts_delete_task_source_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.mysql_dts_drop_user_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow.SubBuilder")
    def test_parallel_mounts_drop_and_delete_task_source(self, mock_sub_builder, mock_drop_user, mock_delete):
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
        self.assertTrue(drop_inp.ignore_errors)
        delete_inp = mock_delete.call_args[0][0]
        self.assertEqual(delete_inp.master_addr, "127.0.0.4:8261")
        self.assertEqual(delete_inp.bk_cloud_id, 0)
        self.assertEqual(delete_inp.task_names, ["t1"])
        self.assertEqual(delete_inp.source_names, ["s1"])
        # drop_user 可 ignore；delete_task_source 成功路径强制不吞错
        self.assertFalse(delete_inp.ignore_errors)
        self.assertEqual(delete_inp.task_mode, "all")
        self.assertEqual(delete_inp.full_load_engine, "builtin")

        delete_sub.build_sub_process.assert_called_once()
        self.assertEqual(str(delete_sub.build_sub_process.call_args.kwargs.get("sub_name")), str(_("清理 dts-task")))

        sub.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=["drop-sub", "delete-sub"])
        sub.add_sub_pipeline.assert_not_called()

    def test_task_clean_module_does_not_import_destroy_stop_tasks(self):
        import backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_delete_task_source_subflow as delete_mod
        import backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow as clean_mod

        self.assertFalse(hasattr(clean_mod, "MysqlDtsStopTasksComponent"))
        self.assertFalse(hasattr(delete_mod, "MysqlDtsStopTasksComponent"))
        self.assertNotIn("stop_tasks", clean_mod.__file__)


class RevokedPathDoesNotCleanRelayOrDumpTest(SimpleTestCase):
    def test_migrate_handler_source_has_no_purge_or_dump_rm(self):
        import backend.flow.signal.mysql_dts_migrate_handler as handler_mod

        self.assertFalse(hasattr(handler_mod, "MySQLDTSApi"))
        self.assertFalse(hasattr(handler_mod, "JobApi"))
        with open(handler_mod.__file__, encoding="utf-8") as handler_src:
            handler_text = handler_src.read()
        self.assertNotIn("purge_relay", handler_text)
        self.assertNotIn("exported_data", handler_text)
        self.assertNotIn("get_full_migrate_data_dir", handler_text)


class OuterRunFlowCleanInputNamesTest(SimpleTestCase):
    def _assert_clean_input_has_ticket_names(self, flow_cls, module_path):
        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        src = SourceSpec(cluster_id=1, source_name="src-ticket", sync_scope=SyncScope(do_dbs=["db"]))
        plan = _minimal_plan(
            task_specs=[
                DtsTaskSpec(
                    task_name="task-ticket",
                    target_cluster_id=2,
                    sources=[src],
                    dts_task_config=DtsTaskConfig(),
                )
            ]
        )

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
            mock_migrate.return_value.build_sub_process.return_value = MagicMock()
            mock_clean.return_value.build_sub_process.return_value = MagicMock()

            flow = flow_cls(root_id="root-outer", data={"bk_biz_id": 1, "ticket_id": 18801, "created_by": "t"})
            flow.run_flow()

            self.assertEqual(
                pipeline.add_sub_pipeline.call_args_list,
                [
                    call(mock_migrate.return_value.build_sub_process.return_value),
                    call(mock_clean.return_value.build_sub_process.return_value),
                ],
            )
            clean_sub_name = mock_clean.return_value.build_sub_process.call_args.kwargs.get("sub_name")
            self.assertEqual(str(clean_sub_name), str(_("dts-task-clean")))
            clean_inp = mock_clean.call_args[0][0]
            self.assertEqual(clean_inp.master_addr, "127.0.0.4:8261")
            self.assertEqual(clean_inp.task_names, ["task-ticket"])
            self.assertEqual(clean_inp.source_names, ["src-ticket"])
            self.assertTrue(clean_inp.ignore_errors)

    def test_mysql_to_mysql_clean_input_ticket_scoped(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate import MysqlToMysqlMigrateFlow

        self._assert_clean_input_has_ticket_names(
            MysqlToMysqlMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate",
        )

    def test_ha_to_cluster_clean_input_ticket_scoped(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate import MysqlHaToClusterMigrateFlow

        self._assert_clean_input_has_ticket_names(
            MysqlHaToClusterMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate",
        )
