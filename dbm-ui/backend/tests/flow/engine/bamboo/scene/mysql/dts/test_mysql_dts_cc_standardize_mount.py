# -*- coding: utf-8 -*-
"""锁定 DTS 部署 / 追加 Worker 在 register_meta 之后挂载 CC 标准化子流程。"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.context import (
    DtsHostSpec,
    MysqlDtsAppendWorkerSubflowInput,
    MysqlDtsDeploySubflowInput,
)
from backend.tests.mock_data import constant


class MysqlDtsCcStandardizeMountTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_worker_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_master_subflow")
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_colocated_host_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_cc_standardize_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.SubBuilder")
    def test_deploy_subflow_mounts_cc_after_register(
        self, mock_sub_builder, mock_cc_std, _mock_colo, mock_master, mock_worker
    ):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow import mysql_dts_deploy_subflow
        from backend.flow.plugins.components.collections.mysql.dts.deploy.register_meta import (
            MysqlDtsRegisterClusterMetaComponent,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mock_master.return_value = MagicMock()
        mock_master.return_value.build_sub_process.return_value = "master-sub"
        mock_worker.return_value = MagicMock()
        mock_worker.return_value.build_sub_process.return_value = "worker-sub"
        mock_cc_std.return_value = MagicMock()
        mock_cc_std.return_value.build_sub_process.return_value = "cc-sub"

        inp = MysqlDtsDeploySubflowInput(
            root_id="root-cc-1",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=0,
            cluster_name="dts-mount",
            master_hosts=[DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)],
            worker_hosts=[DtsHostSpec(ip="127.0.0.3", bk_cloud_id=0)],
            creator="tester",
        )
        mysql_dts_deploy_subflow(inp)

        register_indexes = []
        for idx, call in enumerate(sub.add_act.call_args_list):
            if call.kwargs.get("act_component_code") == MysqlDtsRegisterClusterMetaComponent.code:
                register_indexes.append(idx)
        self.assertEqual(len(register_indexes), 1)

        mock_cc_std.assert_called_once()
        self.assertEqual(mock_cc_std.call_args.kwargs["cluster_name"], "dts-mount")
        self.assertEqual(mock_cc_std.call_args.kwargs["bk_biz_id"], constant.BK_BIZ_ID)
        mock_cc_std.return_value.build_sub_process.assert_called_once()
        # CC 子流程是最后挂上的（register 之后）
        self.assertEqual(sub.add_sub_pipeline.call_args_list[-1].args[0], "cc-sub")

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.mysql_dts_deploy_worker_subflow"
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.mysql_dts_cc_standardize_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.SubBuilder")
    def test_append_worker_mounts_cc(self, mock_sub_builder, mock_cc_std, mock_worker):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow import (
            mysql_dts_append_worker_subflow,
        )

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mock_worker.return_value = MagicMock()
        mock_worker.return_value.build_sub_process.return_value = "worker-sub"
        mock_cc_std.return_value = MagicMock()
        mock_cc_std.return_value.build_sub_process.return_value = "cc-sub"

        inp = MysqlDtsAppendWorkerSubflowInput(
            root_id="root-cc-2",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=0,
            dts_cluster_id=88,
            master_addr="127.0.0.2:18301",
            deploy_path="/data/dts/x",
            new_worker_hosts=[DtsHostSpec(ip="127.0.0.4", bk_cloud_id=0)],
            existing_worker_nodes=[],
            creator="tester",
        )
        mysql_dts_append_worker_subflow(inp)

        mock_cc_std.assert_called_once()
        self.assertEqual(mock_cc_std.call_args.kwargs["dts_cluster_id"], 88)
        self.assertEqual(sub.add_sub_pipeline.call_count, 2)
        self.assertEqual(sub.add_sub_pipeline.call_args_list[-1].args[0], "cc-sub")
