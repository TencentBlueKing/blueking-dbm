# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType


class StopAfterDeploy(Exception):
    """演练流程在部署调用之后还有大量依赖，断言到探针参数即可停下。"""


class MysqlRollbackExerciseSkipProbeTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.SubBuilder")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.generate_valid_domain")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.get_cluster_config")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.get_version_and_charset")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.Package")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.Cluster")
    @patch("backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise.MySQLSingleApplyFlow")
    def test_exercise_standardize_skips_dbha_probe(
        self,
        mock_apply_flow_cls,
        mock_cluster,
        mock_package,
        mock_version,
        mock_config,
        mock_domain,
        mock_sub_builder,
    ):
        from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise import MySQLRollbackExerciseFlow

        cluster = MagicMock()
        cluster.cluster_type = ClusterType.TenDBSingle.value
        cluster.bk_cloud_id = 0
        cluster.db_module_id = 1
        cluster.time_zone = "UTC"
        cluster.name = "exercise"
        cluster.region = "sz"
        cluster.bk_biz_id = 1
        cluster.immute_domain = "exercise.db"
        master = MagicMock()
        master.port = 3306
        cluster.storageinstance_set.filter.return_value.first.return_value = master
        mock_cluster.objects.get.return_value = cluster
        mock_package.get_latest_package.return_value.name = "mysql-5.7.tgz"
        mock_version.return_value = ("utf8mb4", "5.7")
        mock_config.return_value = {}
        mock_domain.return_value = "rb-exercise.db"
        mock_sub_builder.return_value = MagicMock()

        apply_flow = MagicMock()
        apply_flow.deploy_mysql_single_flow.side_effect = StopAfterDeploy
        mock_apply_flow_cls.return_value = apply_flow

        flow = MySQLRollbackExerciseFlow(
            root_id="root-exercise",
            data={
                "ticket_type": "MYSQL_ROLLBACK_EXERCISE",
                "exercise_cluster_id": 1,
                "bk_biz_id": 1,
                "uid": "1",
                "created_by": "tester",
                "rollback_host": {"ip": "127.0.0.2", "bk_host_id": 1, "bk_cloud_id": 0},
            },
        )

        with self.assertRaises(StopAfterDeploy):
            flow.build_rollback_exercise_flow()

        deploy_kwargs = apply_flow.deploy_mysql_single_flow.call_args.kwargs
        self.assertFalse(deploy_kwargs["with_probe"])
