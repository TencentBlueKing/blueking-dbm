# -*- coding: utf-8 -*-
"""锁定 DTS 部署 / 追加 Worker：空闲检查在前，CC 标准化在 register_meta 之后。"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import add_dts_idle_check_subflow, unique_host_ips
from backend.flow.utils.mysql.dts.context import (
    DtsHostSpec,
    MysqlDtsAppendWorkerSubflowInput,
    MysqlDtsDeploySubflowInput,
)
from backend.tests.mock_data import constant


def _fake_idle_check(sub, **_kwargs):
    sub.add_sub_pipeline("idle-sub")


class UniqueHostIpsTest(SimpleTestCase):
    def test_keeps_order_and_drops_duplicates(self):
        hosts = [
            DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0),
            DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0),
            DtsHostSpec(ip="127.0.0.3", bk_cloud_id=0),
        ]
        self.assertEqual(unique_host_ips(hosts), ["127.0.0.2", "127.0.0.3"])


class DtsIdleCheckHelperTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.subflow_common.init_machine_sub_flow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.subflow_common.env")
    def test_mounts_idle_check_with_unique_ips(self, mock_env, mock_init):
        mock_env.SA_CHECK_TEMPLATE_ID = 99
        mock_init.return_value = "idle-built"
        sub = MagicMock()

        add_dts_idle_check_subflow(
            sub,
            root_id="root-idle-1",
            bk_cloud_id=0,
            hosts=[
                DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0),
                DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0),
                DtsHostSpec(ip="127.0.0.3", bk_cloud_id=0),
            ],
        )

        mock_init.assert_called_once_with(
            uid="root-idle-1",
            root_id="root-idle-1",
            bk_cloud_id=0,
            sys_init_ips=[],
            init_check_ips=["127.0.0.2", "127.0.0.3"],
        )
        sub.add_sub_pipeline.assert_called_once_with(sub_flow="idle-built")

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.subflow_common.init_machine_sub_flow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.subflow_common.env")
    def test_skips_when_sa_template_unset(self, mock_env, mock_init):
        mock_env.SA_CHECK_TEMPLATE_ID = None
        sub = MagicMock()

        add_dts_idle_check_subflow(
            sub,
            root_id="root-idle-2",
            bk_cloud_id=0,
            hosts=[DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)],
        )

        mock_init.assert_not_called()
        sub.add_sub_pipeline.assert_not_called()


class MysqlDtsCcStandardizeMountTest(SimpleTestCase):
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.add_dts_idle_check_subflow",
        side_effect=_fake_idle_check,
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_worker_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_master_subflow")
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_colocated_host_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_cc_standardize_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.SubBuilder")
    def test_deploy_subflow_mounts_idle_first_cc_last(
        self, mock_sub_builder, mock_cc_std, _mock_colo, mock_master, mock_worker, mock_idle
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

        mock_idle.assert_called_once()
        idle_kwargs = mock_idle.call_args.kwargs
        self.assertEqual(idle_kwargs["root_id"], "root-cc-1")
        self.assertEqual(idle_kwargs["bk_cloud_id"], 0)
        self.assertEqual([h.ip for h in idle_kwargs["hosts"]], ["127.0.0.2", "127.0.0.3"])

        mock_cc_std.assert_called_once()
        self.assertEqual(mock_cc_std.call_args.kwargs["cluster_name"], "dts-mount")
        self.assertEqual(mock_cc_std.call_args.kwargs["bk_biz_id"], constant.BK_BIZ_ID)
        mock_cc_std.return_value.build_sub_process.assert_called_once()
        self.assertEqual(sub.add_sub_pipeline.call_args_list[0].args[0], "idle-sub")
        self.assertEqual(sub.add_sub_pipeline.call_args_list[-1].args[0], "cc-sub")

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.add_dts_idle_check_subflow",
        side_effect=_fake_idle_check,
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_worker_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_master_subflow")
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_deploy_colocated_host_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.mysql_dts_cc_standardize_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow.SubBuilder")
    def test_deploy_colocated_passes_same_ip_once_to_idle_check(
        self, mock_sub_builder, mock_cc_std, mock_colo, _mock_master, _mock_worker, mock_idle
    ):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow import mysql_dts_deploy_subflow

        sub = MagicMock()
        mock_sub_builder.return_value = sub
        mock_colo.return_value = MagicMock()
        mock_colo.return_value.build_sub_process.return_value = "colo-sub"
        mock_cc_std.return_value = MagicMock()
        mock_cc_std.return_value.build_sub_process.return_value = "cc-sub"

        same = DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)
        mysql_dts_deploy_subflow(
            MysqlDtsDeploySubflowInput(
                root_id="root-cc-colo",
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=0,
                cluster_name="dts-colo",
                master_hosts=[same],
                worker_hosts=[same],
                creator="tester",
            )
        )

        hosts = mock_idle.call_args.kwargs["hosts"]
        self.assertEqual([h.ip for h in hosts], ["127.0.0.2", "127.0.0.2"])
        self.assertEqual(unique_host_ips(hosts), ["127.0.0.2"])

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.add_dts_idle_check_subflow",
        side_effect=_fake_idle_check,
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.mysql_dts_deploy_worker_subflow"
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.mysql_dts_cc_standardize_subflow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow.SubBuilder")
    def test_append_worker_idle_before_deploy_cc_last(self, mock_sub_builder, mock_cc_std, mock_worker, mock_idle):
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

        mock_idle.assert_called_once()
        self.assertEqual([h.ip for h in mock_idle.call_args.kwargs["hosts"]], ["127.0.0.4"])
        mock_cc_std.assert_called_once()
        self.assertEqual(mock_cc_std.call_args.kwargs["dts_cluster_id"], 88)
        self.assertEqual(sub.add_sub_pipeline.call_count, 3)
        self.assertEqual(sub.add_sub_pipeline.call_args_list[0].args[0], "idle-sub")
        self.assertEqual(sub.add_sub_pipeline.call_args_list[1].args[0], "worker-sub")
        self.assertEqual(sub.add_sub_pipeline.call_args_list[-1].args[0], "cc-sub")
