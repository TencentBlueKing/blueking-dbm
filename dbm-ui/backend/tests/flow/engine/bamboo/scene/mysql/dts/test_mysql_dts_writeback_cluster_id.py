# -*- coding: utf-8 -*-
"""migrate 层回写 dts_cluster_id：ensure 之后 sibling act + 按 ID/按名加载。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_ensure_cluster_subflow import (
    MysqlDtsResolveClusterComponent,
    MysqlDtsResolveClusterService,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.prepare_user import (
    MysqlDtsPrepareMigrateUserComponent,
)
from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.context import (
    DtsHostSpec,
    MysqlDtsDeploySubflowInput,
    MysqlDtsMigrateSubflowInput,
    MysqlDtsTransData,
)
from backend.flow.utils.mysql.dts.migrate_credentials import DtsGrantTarget


def _cluster(**overrides):
    cluster = SimpleNamespace(
        id=7,
        master_addr="127.0.0.2:8261",
        bk_cloud_id=0,
        master_nodes=[{"ip": "127.0.0.2"}],
        worker_nodes=[{"ip": "127.0.0.3"}],
    )
    for key, value in overrides.items():
        setattr(cluster, key, value)
    return cluster


def _run_resolve(kwargs, *, cluster=None):
    service = MysqlDtsResolveClusterService()
    service.log_info = MagicMock()
    service.log_error = MagicMock()
    trans_data = MysqlDtsTransData()
    data = MagicMock()
    data.get_one_of_inputs.side_effect = lambda key: {"kwargs": kwargs, "trans_data": trans_data}.get(key)
    data.outputs = {}
    with patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_ensure_cluster_subflow.MysqlDtsCluster.objects"
    ) as mock_objects:
        mock_objects.filter.return_value.first.return_value = cluster
        ok = service._execute(data, parent_data=None)
    return ok, data, trans_data, mock_objects


class MysqlDtsResolveClusterWritebackTest(SimpleTestCase):
    def test_plan_id_loads_cluster_and_outputs_trans_data(self):
        cluster = _cluster(id=9, master_addr="127.0.0.4:8261", bk_cloud_id=2)
        ok, data, trans_data, mock_objects = _run_resolve({"dts_cluster_id": 9}, cluster=cluster)
        self.assertTrue(ok)
        mock_objects.filter.assert_called_once_with(id=9)
        self.assertEqual(trans_data.migrate_context.dts_cluster_id, 9)
        self.assertEqual(trans_data.migrate_context.master_addr, "127.0.0.4:8261")
        self.assertEqual(trans_data.migrate_context.bk_cloud_id, 2)
        self.assertIs(data.outputs["trans_data"], trans_data)

    def test_name_lookup_writes_registered_id(self):
        cluster = _cluster(id=11)
        ok, data, trans_data, mock_objects = _run_resolve(
            {"dts_cluster_id": 0, "bk_biz_id": 20, "cluster_name": "dts-bkapp-svr02"},
            cluster=cluster,
        )
        self.assertTrue(ok)
        unused_args, filter_kwargs = mock_objects.filter.call_args
        self.assertFalse(unused_args)
        self.assertEqual(filter_kwargs["bk_biz_id"], 20)
        self.assertEqual(filter_kwargs["name"], "dts-bkapp-svr02")
        self.assertIn("deploying", filter_kwargs["status__in"])
        self.assertIn("running", filter_kwargs["status__in"])
        self.assertEqual(trans_data.migrate_context.dts_cluster_id, 11)
        self.assertIs(data.outputs["trans_data"], trans_data)

    def test_missing_row_fails(self):
        ok, unused_data, trans_data, unused_objects = _run_resolve(
            {"dts_cluster_id": 0, "bk_biz_id": 20, "cluster_name": "missing"},
            cluster=None,
        )
        self.assertFalse(ok)
        self.assertIsNone(trans_data.migrate_context.dts_cluster_id)


def _minimal_plan(**overrides):
    plan = SimpleNamespace(
        topology=MigrateTopology.ONE_TO_ONE.value,
        task_specs=[],
        dts_cluster_id=None,
        auto_deploy_dts=False,
        deploy_subflow_inp=MysqlDtsDeploySubflowInput(
            root_id="root-abc",
            bk_biz_id=20,
            bk_cloud_id=0,
            cluster_name="dts-bkapp-svr02",
            master_hosts=[DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)],
            worker_hosts=[DtsHostSpec(ip="127.0.0.3", bk_cloud_id=0)],
        ),
        dts_lifecycle="deploy",
        worker_count_required=0,
        bk_biz_id=20,
        bk_cloud_id=0,
    )
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


class MysqlDtsMigrateSubflowWritebackActTest(SimpleTestCase):
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
            ["127.0.0.1"],
            [DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=100)],
        ),
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.resolve_master_addr_from_plan",
        return_value="127.0.0.4:8261",
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.mysql_dts_ensure_cluster_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow.SubBuilder")
    def test_writeback_act_follows_ensure_cluster(self, mock_sub_builder, mock_ensure, *_mocks):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow import mysql_dts_migrate_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mock_ensure.return_value.build_sub_process.return_value = MagicMock()

        inp = MysqlDtsMigrateSubflowInput(
            root_id="root-abc",
            bk_biz_id=20,
            ticket_id=18801,
            migrate_plan=_minimal_plan(),
            creator="tester",
        )
        mysql_dts_migrate_subflow(inp)

        codes = [call.kwargs.get("act_component_code") for call in sub.add_act.call_args_list]
        self.assertNotIn(MysqlDtsResolveClusterComponent.code, codes)
        self.assertIn(MysqlDtsPrepareMigrateUserComponent.code, codes)
        prepare_kwargs = next(
            call.kwargs["kwargs"]
            for call in sub.add_act.call_args_list
            if call.kwargs.get("act_component_code") == MysqlDtsPrepareMigrateUserComponent.code
        )
        self.assertEqual(prepare_kwargs["bk_biz_id"], 20)
        self.assertEqual(prepare_kwargs["cluster_name"], "dts-bkapp-svr02")
        self.assertIsNone(prepare_kwargs["dts_cluster_id"])
