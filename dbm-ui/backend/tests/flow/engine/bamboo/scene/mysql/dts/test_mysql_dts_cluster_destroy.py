# -*- coding: utf-8 -*-
"""MYSQL_DTS_CLUSTER_DESTROY：单 ID 串行、多 ID 并行 cleanup。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.models import MysqlDtsCluster


def _cluster(cid: int, name: str, path: str):
    return SimpleNamespace(
        id=cid,
        bk_biz_id=1,
        bk_cloud_id=0,
        master_addr=f"127.0.0.{cid}:8261",
        master_nodes=[{"ip": f"127.0.0.{cid}", "bk_cloud_id": 0}],
        worker_nodes=[{"ip": f"127.0.0.{cid + 10}", "bk_cloud_id": 0}],
        deploy_path=path,
        name=name,
    )


class MysqlDtsClusterDestroyFlowTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.mysql_dts_cleanup_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.MysqlDtsCluster.objects.filter")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.Builder")
    def test_single_cluster_id_serial(self, mock_builder, mock_filter, mock_cleanup):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy import MysqlDtsClusterDestroyFlow

        cluster = _cluster(9, "dts-a", "/data/dts/a")
        mock_filter.return_value = [cluster]
        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        built = MagicMock(name="cleanup-9")
        mock_cleanup.return_value.build_sub_process.return_value = built

        MysqlDtsClusterDestroyFlow(
            root_id="root-destroy-1",
            data={"dts_cluster_id": 9, "created_by": "t", "recycle_hosts": True},
        ).run_flow()

        pipeline.add_sub_pipeline.assert_called_once_with(built)
        pipeline.add_parallel_sub_pipeline.assert_not_called()
        cleanup_inp = mock_cleanup.call_args[0][0]
        self.assertEqual(cleanup_inp.dts_cluster_id, 9)
        self.assertEqual(cleanup_inp.cluster_name, "dts-a")
        pipeline.run_pipeline.assert_called_once()

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.mysql_dts_cleanup_subflow")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.MysqlDtsCluster.objects.filter")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.Builder")
    def test_cluster_ids_parallel(self, mock_builder, mock_filter, mock_cleanup):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy import MysqlDtsClusterDestroyFlow

        c9 = _cluster(9, "dts-a", "/data/dts/a")
        c10 = _cluster(10, "dts-b", "/data/dts/b")
        mock_filter.return_value = [c9, c10]
        pipeline = MagicMock()
        mock_builder.return_value = pipeline
        built = [MagicMock(name="cleanup-9"), MagicMock(name="cleanup-10")]
        mock_cleanup.return_value.build_sub_process.side_effect = built

        MysqlDtsClusterDestroyFlow(
            root_id="root-destroy-2",
            data={"dts_cluster_ids": [9, 10], "created_by": "t", "recycle_hosts": True},
        ).run_flow()

        pipeline.add_sub_pipeline.assert_not_called()
        pipeline.add_parallel_sub_pipeline.assert_called_once_with(sub_flow_list=built)
        ids = [c[0][0].dts_cluster_id for c in mock_cleanup.call_args_list]
        self.assertEqual(ids, [9, 10])

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy.MysqlDtsCluster.objects.filter")
    def test_missing_cluster_raises(self, mock_filter):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cluster_destroy import MysqlDtsClusterDestroyFlow

        mock_filter.return_value = []
        with self.assertRaises(MysqlDtsCluster.DoesNotExist):
            MysqlDtsClusterDestroyFlow(
                root_id="root-destroy-miss",
                data={"dts_cluster_ids": [9, 10], "created_by": "t"},
            ).run_flow()
