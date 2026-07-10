# -*- coding: utf-8 -*-
"""覆盖 DTS migrate 子流程 SubBuilder data 必须含 uid（add_parallel_acts 硬取）。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.context import MysqlDtsDropUserSubflowInput, MysqlDtsMigrateSubflowInput
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


class MysqlDtsMigrateSubflowUidTest(SimpleTestCase):
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
    def test_migrate_subflow_data_contains_uid(self, mock_sub_builder, mock_ensure, *_mocks):
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

        unused_args, kwargs = mock_sub_builder.call_args
        data = kwargs["data"]
        self.assertEqual(data["uid"], 18801)
        self.assertEqual(data["ticket_id"], 18801)
        self.assertEqual(data["bk_biz_id"], 1)
        self.assertEqual(data["created_by"], "tester")
        sub.add_parallel_acts.assert_called_once()


class MysqlDtsDropUserSubflowUidTest(SimpleTestCase):
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_drop_user_subflow.build_dts_drop_user_parallel_acts",
        return_value=[{"act_name": "drop", "act_component_code": "x", "kwargs": {}}],
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_drop_user_subflow.SubBuilder")
    def test_drop_user_subflow_data_contains_uid(self, mock_sub_builder, _mock_acts):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_drop_user_subflow import mysql_dts_drop_user_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        inp = MysqlDtsDropUserSubflowInput(
            root_id="root-drop",
            bk_biz_id=1,
            dts_user="dts_u",
            grant_hosts=["127.0.0.3"],
            grant_targets=[{"bk_cloud_id": 0, "address": "127.0.0.2:3306"}],
            creator="tester",
        )
        mysql_dts_drop_user_subflow(inp)

        unused_args, kwargs = mock_sub_builder.call_args
        self.assertEqual(kwargs["data"]["uid"], "root-drop")
        sub.add_parallel_acts.assert_called_once()
