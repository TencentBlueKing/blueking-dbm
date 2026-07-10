# -*- coding: utf-8 -*-
"""保证 DTS migrate Act kwargs 不含 dataclass，可被 bamboo codec JSON 序列化。"""
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.constants import FullLoadEngine, MigrateTopology, MigrateType
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskConfig,
    DtsTaskSpec,
    SourceSpec,
    SyncScope,
    contains_dataclass,
    dts_migrate_plan_from_dict,
    dts_migrate_plan_to_dict,
    dts_task_spec_from_dict,
    dts_task_spec_to_dict,
)


def _builtin_task_spec(**overrides) -> DtsTaskSpec:
    spec = DtsTaskSpec(
        task_name="mysql-dts-18801-100-200",
        target_cluster_id=200,
        sources=[
            SourceSpec(
                cluster_id=100,
                source_name="src-1",
                sync_scope=SyncScope(do_dbs=["db_a"]),
                worker_name="worker-1",
            )
        ],
        dts_task_config=DtsTaskConfig(full_load_engine=FullLoadEngine.BUILTIN.value),
    )
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def _minimal_plan(task_spec: DtsTaskSpec | None = None) -> DtsMigratePlan:
    task_spec = task_spec or _builtin_task_spec()
    return DtsMigratePlan(
        topology=MigrateTopology.ONE_TO_ONE.value,
        migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
        dts_cluster_id=1,
        dts_lifecycle="use_existing",
        auto_deploy_dts=False,
        deploy_subflow_inp=None,
        cleanup_after_migrate=False,
        recycle_dts_hosts=True,
        dts_task_config=DtsTaskConfig(full_load_engine=FullLoadEngine.BUILTIN.value),
        task_specs=[task_spec],
        worker_count_required=1,
        bk_biz_id=3,
        bk_cloud_id=0,
    )


class DtsPlanSerializeTest(SimpleTestCase):
    def test_task_spec_roundtrip_json(self):
        original = _builtin_task_spec()
        payload = dts_task_spec_to_dict(original)
        self.assertFalse(contains_dataclass(payload))
        json.dumps(payload)
        restored = dts_task_spec_from_dict(payload)
        self.assertEqual(restored.task_name, original.task_name)
        self.assertEqual(restored.target_cluster_id, original.target_cluster_id)
        self.assertEqual(restored.sources[0].cluster_id, 100)
        self.assertEqual(restored.sources[0].worker_name, "worker-1")
        self.assertEqual(restored.sources[0].sync_scope.do_dbs, ["db_a"])

    def test_migrate_plan_roundtrip_json(self):
        original = _minimal_plan()
        payload = dts_migrate_plan_to_dict(original)
        self.assertFalse(contains_dataclass(payload))
        json.dumps(payload)
        restored = dts_migrate_plan_from_dict(payload)
        self.assertEqual(restored.migrate_type, original.migrate_type)
        self.assertEqual(restored.task_specs[0].task_name, original.task_specs[0].task_name)
        self.assertEqual(restored.dts_cluster_id, 1)


class MysqlDtsMigrateTaskSubflowKwargsTest(SimpleTestCase):
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_catchup_cutover_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.SubBuilder")
    def test_act_kwargs_are_json_serializable(self, mock_sub_builder, mock_catchup):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import (
            mysql_dts_migrate_task_subflow,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        fake_catchup = MagicMock()
        fake_catchup.build_sub_process.return_value = MagicMock(name="catchup")
        mock_catchup.return_value = fake_catchup

        plan = _minimal_plan()
        task_spec = plan.task_specs[0]
        mysql_dts_migrate_task_subflow(
            root_id="root-kwargs",
            bk_biz_id=3,
            ticket_id=18801,
            master_addr="127.0.0.1:18301",
            task_spec=task_spec,
            migrate_plan=plan,
            creator="tester",
        )

        self.assertTrue(sub.add_act.called)
        for call in sub.add_act.call_args_list:
            kwargs = call.kwargs["kwargs"]
            self.assertIsInstance(kwargs, dict)
            self.assertFalse(contains_dataclass(kwargs), msg=f"dataclass leaked in act kwargs: {call}")
            json.dumps(kwargs)
            if "task_spec" in kwargs:
                self.assertIsInstance(kwargs["task_spec"], dict)
            if "migrate_plan" in kwargs:
                self.assertIsInstance(kwargs["migrate_plan"], dict)

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_catchup_cutover_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.SubBuilder")
    def test_builtin_all_inserts_poll_full_load_before_catchup(self, mock_sub_builder, mock_catchup):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import (
            mysql_dts_migrate_task_subflow,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load import (
            MysqlDtsPollFullLoadComponent,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        fake_catchup = MagicMock()
        fake_catchup.build_sub_process.return_value = MagicMock(name="catchup")
        mock_catchup.return_value = fake_catchup

        task_spec = _builtin_task_spec()
        task_spec.dts_task_config.task_mode = "all"
        plan = _minimal_plan(task_spec)
        mysql_dts_migrate_task_subflow(
            root_id="root-full-load-all",
            bk_biz_id=3,
            ticket_id=18801,
            master_addr="127.0.0.1:18301",
            task_spec=task_spec,
            migrate_plan=plan,
            creator="tester",
        )

        act_codes = [c.kwargs["act_component_code"] for c in sub.add_act.call_args_list]
        self.assertIn(MysqlDtsPollFullLoadComponent.code, act_codes)
        full_load_call = next(
            c
            for c in sub.add_act.call_args_list
            if c.kwargs["act_component_code"] == MysqlDtsPollFullLoadComponent.code
        )
        self.assertEqual(full_load_call.kwargs["kwargs"]["task_mode"], "all")
        # update_meta → poll_full_load → catchup sub_pipeline
        update_idx = next(
            i
            for i, c in enumerate(sub.add_act.call_args_list)
            if c.kwargs["act_component_code"] == "mysql_dts_update_meta"
        )
        full_idx = next(
            i
            for i, c in enumerate(sub.add_act.call_args_list)
            if c.kwargs["act_component_code"] == MysqlDtsPollFullLoadComponent.code
        )
        self.assertLess(update_idx, full_idx)
        self.assertTrue(sub.add_sub_pipeline.called)
        mock_catchup.assert_called_once()

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_catchup_cutover_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.SubBuilder")
    def test_builtin_full_also_inserts_poll_full_load(self, mock_sub_builder, mock_catchup):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import (
            mysql_dts_migrate_task_subflow,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load import (
            MysqlDtsPollFullLoadComponent,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        fake_catchup = MagicMock()
        fake_catchup.build_sub_process.return_value = MagicMock(name="catchup")
        mock_catchup.return_value = fake_catchup

        task_spec = _builtin_task_spec()
        task_spec.dts_task_config.task_mode = "full"
        plan = _minimal_plan(task_spec)
        mysql_dts_migrate_task_subflow(
            root_id="root-full-load-full",
            bk_biz_id=3,
            ticket_id=18801,
            master_addr="127.0.0.1:18301",
            task_spec=task_spec,
            migrate_plan=plan,
            creator="tester",
        )

        act_codes = [c.kwargs["act_component_code"] for c in sub.add_act.call_args_list]
        self.assertIn(MysqlDtsPollFullLoadComponent.code, act_codes)
        full_load_call = next(
            c
            for c in sub.add_act.call_args_list
            if c.kwargs["act_component_code"] == MysqlDtsPollFullLoadComponent.code
        )
        self.assertEqual(full_load_call.kwargs["kwargs"]["task_mode"], "full")

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_myloader_import_subflow"
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_catchup_cutover_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.SubBuilder")
    def test_myloader_does_not_insert_poll_full_load(self, mock_sub_builder, mock_catchup, mock_myloader):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import (
            mysql_dts_migrate_task_subflow,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load import (
            MysqlDtsPollFullLoadComponent,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        fake_catchup = MagicMock()
        fake_catchup.build_sub_process.return_value = MagicMock(name="catchup")
        mock_catchup.return_value = fake_catchup
        fake_myloader = MagicMock()
        fake_myloader.build_sub_process.return_value = MagicMock(name="myloader")
        mock_myloader.return_value = fake_myloader

        task_spec = _builtin_task_spec()
        task_spec.dts_task_config.full_load_engine = FullLoadEngine.MYLOADER.value
        plan = _minimal_plan(task_spec)
        plan.dts_task_config.full_load_engine = FullLoadEngine.MYLOADER.value
        mysql_dts_migrate_task_subflow(
            root_id="root-myloader",
            bk_biz_id=3,
            ticket_id=18801,
            master_addr="127.0.0.1:18301",
            task_spec=task_spec,
            migrate_plan=plan,
            creator="tester",
        )

        act_codes = [c.kwargs["act_component_code"] for c in sub.add_act.call_args_list]
        self.assertNotIn(MysqlDtsPollFullLoadComponent.code, act_codes)
        for call in sub.add_sub_pipeline.call_args_list:
            # myloader / catchup 子流程名不应伪装为全量等待组件 code
            self.assertNotEqual(
                getattr(call.kwargs.get("sub_flow"), "code", None),
                MysqlDtsPollFullLoadComponent.code,
            )
