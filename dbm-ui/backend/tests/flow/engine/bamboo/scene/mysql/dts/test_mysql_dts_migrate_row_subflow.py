# -*- coding: utf-8 -*-
"""多行 one_to_one：行子流程并行 + 凭证隔离。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.constants import MigrateTopology, MigrateType
from backend.flow.utils.mysql.dts.migrate_credentials import DtsGrantTarget

_ROW_MOD = "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow"


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
        migrate_type="",
        dts_task_config=None,
    )
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


class BuildMigrateRowSubNameTest(SimpleTestCase):
    def test_one_to_one_uses_src_and_dst_cluster_id(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import build_migrate_row_sub_name

        spec = SimpleNamespace(
            target_cluster_id=333,
            sources=[SimpleNamespace(cluster_id=322)],
        )
        self.assertEqual(build_migrate_row_sub_name(_minimal_plan(task_specs=[spec])), "322 迁移-> 333")

    def test_many_to_one_joins_source_ids(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import build_migrate_row_sub_name

        spec = SimpleNamespace(
            target_cluster_id=200,
            sources=[SimpleNamespace(cluster_id=100), SimpleNamespace(cluster_id=101)],
        )
        self.assertEqual(build_migrate_row_sub_name(_minimal_plan(task_specs=[spec])), "100,101 迁移-> 200")

    def test_missing_specs_fallback(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import build_migrate_row_sub_name

        self.assertEqual(build_migrate_row_sub_name(_minimal_plan()), "- 迁移-> -")


class BuildParallelMigrateRowPipelinesTest(SimpleTestCase):
    def test_two_rows_parallel_isolated_credentials(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import (
            build_parallel_migrate_row_pipelines,
        )

        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        plans = [
            _minimal_plan(
                dts_cluster_id=9,
                task_specs=[SimpleNamespace(target_cluster_id=333, sources=[SimpleNamespace(cluster_id=322)])],
            ),
            _minimal_plan(
                dts_cluster_id=10,
                task_specs=[SimpleNamespace(target_cluster_id=335, sources=[SimpleNamespace(cluster_id=324)])],
            ),
        ]
        pipeline = MagicMock()

        with patch(f"{_ROW_MOD}.resolve_migrate_temp_account_for_pipeline") as mock_acct, patch(
            f"{_ROW_MOD}.resolve_master_addr_from_plan", return_value="127.0.0.4:8261"
        ), patch(f"{_ROW_MOD}.mysql_dts_migrate_subflow") as mock_migrate, patch(
            f"{_ROW_MOD}.mysql_dts_task_clean_subflow"
        ) as mock_clean, patch(
            f"{_ROW_MOD}.SubBuilder"
        ) as mock_sub_builder:
            mock_acct.side_effect = [
                ("dts_m_row0", "pwd0", ["127.0.0.3"], grant_targets),
                ("dts_m_row1", "pwd1", ["127.0.0.5"], grant_targets),
            ]
            row_pipes = [MagicMock(name="row0"), MagicMock(name="row1")]
            row_built = [MagicMock(name="built0"), MagicMock(name="built1")]
            mock_sub_builder.side_effect = row_pipes
            for rp, built in zip(row_pipes, row_built):
                rp.build_sub_process.return_value = built
            mock_migrate.return_value.build_sub_process.return_value = MagicMock()
            mock_clean.return_value.build_sub_process.return_value = MagicMock()

            build_parallel_migrate_row_pipelines(
                pipeline=pipeline,
                root_id="root-multi",
                data={"bk_biz_id": 1, "ticket_id": 19943, "created_by": "t"},
                migrate_plans=plans,
                migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
            )

            pipeline.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=row_built)
            self.assertEqual(mock_acct.call_count, 2)
            migrate_users = [c[0][0].dts_user for c in mock_migrate.call_args_list]
            clean_users = [c[0][0].dts_user for c in mock_clean.call_args_list]
            self.assertEqual(migrate_users, ["dts_m_row0", "dts_m_row1"])
            self.assertEqual(clean_users, ["dts_m_row0", "dts_m_row1"])
            self.assertEqual(plans[0].migrate_type, MigrateType.MYSQL_TO_MYSQL.value)
            self.assertEqual(plans[1].migrate_type, MigrateType.MYSQL_TO_MYSQL.value)
            self.assertNotEqual(migrate_users[0], migrate_users[1])
            self.assertEqual(row_pipes[0].build_sub_process.call_args.kwargs["sub_name"], "322 迁移-> 333")
            self.assertEqual(row_pipes[1].build_sub_process.call_args.kwargs["sub_name"], "324 迁移-> 335")

    def test_single_row_still_one_parallel_branch(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import (
            build_parallel_migrate_row_pipelines,
        )

        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        pipeline = MagicMock()
        with patch(
            f"{_ROW_MOD}.resolve_migrate_temp_account_for_pipeline",
            return_value=("dts_m_one", "pwd", ["127.0.0.3"], grant_targets),
        ), patch(f"{_ROW_MOD}.resolve_master_addr_from_plan", return_value="127.0.0.4:8261"), patch(
            f"{_ROW_MOD}.mysql_dts_migrate_subflow"
        ) as mock_migrate, patch(
            f"{_ROW_MOD}.mysql_dts_task_clean_subflow"
        ) as mock_clean, patch(
            f"{_ROW_MOD}.SubBuilder"
        ) as mock_sub_builder:
            row_pipe = MagicMock()
            row_built = MagicMock(name="built-one")
            mock_sub_builder.return_value = row_pipe
            row_pipe.build_sub_process.return_value = row_built
            mock_migrate.return_value.build_sub_process.return_value = MagicMock()
            mock_clean.return_value.build_sub_process.return_value = MagicMock()

            build_parallel_migrate_row_pipelines(
                pipeline=pipeline,
                root_id="root-one",
                data={"bk_biz_id": 1, "ticket_id": 12, "created_by": "t"},
                migrate_plans=[_minimal_plan()],
                migrate_type=MigrateType.HA_TO_CLUSTER.value,
            )

            pipeline.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=[row_built])
            self.assertEqual(
                row_pipe.add_sub_pipeline.call_args_list,
                [
                    call(mock_migrate.return_value.build_sub_process.return_value),
                    call(mock_clean.return_value.build_sub_process.return_value),
                ],
            )

    def test_optional_migrate_type_keeps_plan_value(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import (
            build_parallel_migrate_row_pipelines,
        )

        grant_targets = [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1)]
        plans = [
            _minimal_plan(migrate_type=MigrateType.HA_TO_CLUSTER.value),
            _minimal_plan(migrate_type=MigrateType.MYSQL_TO_MYSQL.value),
        ]
        pipeline = MagicMock()
        with patch(
            f"{_ROW_MOD}.resolve_migrate_temp_account_for_pipeline",
            return_value=("dts_m_mix", "pwd", ["127.0.0.3"], grant_targets),
        ), patch(f"{_ROW_MOD}.resolve_master_addr_from_plan", return_value="127.0.0.4:8261"), patch(
            f"{_ROW_MOD}.mysql_dts_migrate_subflow"
        ), patch(
            f"{_ROW_MOD}.mysql_dts_task_clean_subflow"
        ), patch(
            f"{_ROW_MOD}.SubBuilder"
        ) as mock_sub_builder:
            row_pipe = MagicMock()
            mock_sub_builder.return_value = row_pipe
            row_pipe.build_sub_process.return_value = MagicMock()
            build_parallel_migrate_row_pipelines(
                pipeline=pipeline,
                root_id="root-keep",
                data={"bk_biz_id": 1, "ticket_id": 12, "created_by": "t"},
                migrate_plans=plans,
            )
        self.assertEqual(plans[0].migrate_type, MigrateType.HA_TO_CLUSTER.value)
        self.assertEqual(plans[1].migrate_type, MigrateType.MYSQL_TO_MYSQL.value)


class OneToOneSceneParallelRowsTest(SimpleTestCase):
    def _assert_scene_passes_n_plans(self, flow_cls, module_path, migrate_type, n_plans):
        plans = [_minimal_plan(dts_cluster_id=i) for i in range(n_plans)]
        with patch(f"{module_path}.resolve_migrate_plans_from_ticket_data", return_value=plans), patch(
            f"{module_path}.build_parallel_migrate_row_pipelines"
        ) as mock_build, patch(f"{module_path}.Builder") as mock_builder:
            pipeline = MagicMock()
            mock_builder.return_value = pipeline
            flow = flow_cls(root_id="root-scene", data={"bk_biz_id": 1, "ticket_id": 19943, "created_by": "t"})
            flow.run_flow()
            mock_build.assert_called_once()
            kwargs = mock_build.call_args.kwargs
            self.assertEqual(kwargs["migrate_plans"], plans)
            self.assertEqual(kwargs["migrate_type"], migrate_type)
            self.assertIs(kwargs["pipeline"], pipeline)
            pipeline.run_pipeline.assert_called_once()

    def test_mysql_to_mysql_two_rows(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate import MysqlToMysqlMigrateFlow
        from backend.flow.utils.mysql.dts.constants import MigrateType as MT

        self._assert_scene_passes_n_plans(
            MysqlToMysqlMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate",
            MT.MYSQL_TO_MYSQL.value,
            2,
        )

    def test_ha_to_cluster_two_rows(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate import MysqlHaToClusterMigrateFlow
        from backend.flow.utils.mysql.dts.constants import MigrateType as MT

        self._assert_scene_passes_n_plans(
            MysqlHaToClusterMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_ha_to_cluster_migrate",
            MT.HA_TO_CLUSTER.value,
            2,
        )

    def test_mysql_to_mysql_single_row(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate import MysqlToMysqlMigrateFlow
        from backend.flow.utils.mysql.dts.constants import MigrateType as MT

        self._assert_scene_passes_n_plans(
            MysqlToMysqlMigrateFlow,
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_to_mysql_migrate",
            MT.MYSQL_TO_MYSQL.value,
            1,
        )

    def test_rename_keeps_per_plan_migrate_type(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_rename_migrate import MysqlRenameMigrateFlow
        from backend.flow.utils.mysql.dts.constants import MigrateType as MT

        module_path = "backend.flow.engine.bamboo.scene.mysql.dts.mysql_rename_migrate"
        plans = [
            _minimal_plan(migrate_type=MT.MYSQL_TO_MYSQL.value),
            _minimal_plan(migrate_type=MT.HA_TO_CLUSTER.value),
        ]
        with patch(f"{module_path}.resolve_migrate_plans_from_ticket_data", return_value=plans), patch(
            f"{module_path}.build_parallel_migrate_row_pipelines"
        ) as mock_build, patch(f"{module_path}.Builder") as mock_builder:
            pipeline = MagicMock()
            mock_builder.return_value = pipeline
            MysqlRenameMigrateFlow(
                root_id="root-rename", data={"bk_biz_id": 1, "ticket_id": 19943, "created_by": "t"}
            ).run_flow()
            kwargs = mock_build.call_args.kwargs
            self.assertIsNone(kwargs.get("migrate_type"))
            self.assertEqual(kwargs["migrate_plans"][0].migrate_type, MT.MYSQL_TO_MYSQL.value)
            self.assertEqual(kwargs["migrate_plans"][1].migrate_type, MT.HA_TO_CLUSTER.value)
            pipeline.run_pipeline.assert_called_once()
