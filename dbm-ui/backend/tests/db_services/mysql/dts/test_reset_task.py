# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.types import (
    CreateTaskRequest,
    SourceConfig,
    SourceConfItem,
    TargetConfig,
    Task,
    TaskStatusItem,
    TaskStatusListResponse,
)
from backend.db_meta.models import MysqlDtsCluster
from backend.db_services.mysql.dts.handlers import MySQLDtsMigrateHandler


class ResetDtsTaskHandlerTest(SimpleTestCase):
    def setUp(self):
        self.task_name = "task-demo"
        self.dts_cluster_id = 101
        self.master_addr = "127.0.0.1:1083"
        self.cluster = MagicMock()
        self.cluster.master_addr = self.master_addr
        self.cluster.bk_cloud_id = 0
        self.bk_cloud_id = 0
        self.task = Task(
            name=self.task_name,
            task_mode="all",
            target_config=TargetConfig(
                host="127.0.0.2",
                port=3306,
                user="dts",
                password="pwd",
            ),
            source_config=SourceConfig(
                source_conf=[
                    SourceConfItem(
                        source_name="source-1",
                        binlog_name="binlog.000001",
                        binlog_pos=123,
                        binlog_gtid="gtid-1",
                    )
                ]
            ),
        )

    def _status_resp(self, *items: TaskStatusItem) -> TaskStatusListResponse:
        return TaskStatusListResponse(total=len(items), data=list(items))

    def _item(self, *, stage: str, error_msg: str | None = None) -> TaskStatusItem:
        return TaskStatusItem(name=self.task_name, stage=stage, error_msg=error_msg)

    def _assert_reset_sequence(self, mock_api):
        mock_api.get_task.assert_called_once_with(self.master_addr, self.task_name, bk_cloud_id=self.bk_cloud_id)
        mock_api.delete_task.assert_called_once_with(
            self.master_addr, self.task_name, force=True, bk_cloud_id=self.bk_cloud_id
        )
        mock_api.create_task.assert_called_once()
        create_args = mock_api.create_task.call_args[0]
        create_kwargs = mock_api.create_task.call_args.kwargs
        self.assertEqual(create_args[0], self.master_addr)
        self.assertIsInstance(create_args[1], CreateTaskRequest)
        self.assertEqual(create_args[1].task.name, self.task_name)
        self.assertEqual(create_kwargs.get("bk_cloud_id"), self.bk_cloud_id)
        src = create_args[1].task.source_config.source_conf[0]
        self.assertEqual(src.binlog_name, "")
        self.assertEqual(src.binlog_pos, 0)
        self.assertEqual(src.binlog_gtid, "")
        mock_api.start_task.assert_called_once_with(self.master_addr, self.task_name, bk_cloud_id=self.bk_cloud_id)
        mock_api.stop_task.assert_not_called()

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_healthy_running_rejects_without_mutate(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        mock_api.get_task_status.return_value = self._status_resp(self._item(stage="Running"))

        with self.assertRaises(ValueError) as ctx:
            MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        self.assertIn("不允许 reset", str(ctx.exception))
        mock_api.get_task.assert_not_called()
        mock_api.delete_task.assert_not_called()
        mock_api.create_task.assert_not_called()
        mock_api.start_task.assert_not_called()

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_running_with_error_msg_allows_reset(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        mock_api.get_task_status.return_value = self._status_resp(self._item(stage="Running", error_msg="dump failed"))
        mock_api.get_task.return_value = self.task

        result = MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        self._assert_reset_sequence(mock_api)
        self.assertEqual(
            result,
            {
                "task_name": self.task_name,
                "dts_cluster_id": self.dts_cluster_id,
                "master_addr": self.master_addr,
                "bk_cloud_id": self.bk_cloud_id,
                "action": "reset",
            },
        )

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_paused_or_stopped_allows_reset(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        for stage in ("Paused", "Stopped"):
            mock_api.reset_mock()
            mock_api.get_task_status.return_value = self._status_resp(self._item(stage=stage))
            mock_api.get_task.return_value = self.task.model_copy(deep=True)

            result = MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

            self._assert_reset_sequence(mock_api)
            self.assertEqual(result["action"], "reset")

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_multi_item_one_healthy_running_rejects(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        mock_api.get_task_status.return_value = self._status_resp(
            self._item(stage="Paused"),
            self._item(stage="running", error_msg="  "),
            self._item(stage="Stopped", error_msg="old"),
        )

        with self.assertRaises(ValueError):
            MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        mock_api.get_task.assert_not_called()
        mock_api.delete_task.assert_not_called()
        mock_api.start_task.assert_not_called()

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_cluster_missing_raises(self, mock_get, mock_api):
        mock_get.side_effect = MysqlDtsCluster.DoesNotExist()

        with self.assertRaises(ValueError) as ctx:
            MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        self.assertIn("不存在", str(ctx.exception))
        mock_api.get_task_status.assert_not_called()
        mock_api.start_task.assert_not_called()

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_get_task_status_failure_no_mutate(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        mock_api.get_task_status.side_effect = RuntimeError("master down")

        with self.assertRaises(ValueError) as ctx:
            MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        self.assertIn("查询 DTS 任务状态失败", str(ctx.exception))
        mock_api.get_task.assert_not_called()
        mock_api.delete_task.assert_not_called()
        mock_api.start_task.assert_not_called()

    @patch("backend.db_services.mysql.dts.handlers.MySQLDTSApi")
    @patch("backend.db_services.mysql.dts.handlers.MysqlDtsCluster.objects.get")
    def test_get_task_failure_no_delete(self, mock_get, mock_api):
        mock_get.return_value = self.cluster
        mock_api.get_task_status.return_value = self._status_resp(self._item(stage="Paused"))
        mock_api.get_task.side_effect = RuntimeError("task missing")

        with self.assertRaises(ValueError) as ctx:
            MySQLDtsMigrateHandler.reset_task(self.task_name, self.dts_cluster_id)

        self.assertIn("获取 DTS 任务配置失败", str(ctx.exception))
        mock_api.delete_task.assert_not_called()
        mock_api.create_task.assert_not_called()
        mock_api.start_task.assert_not_called()
        # call order guard: status then get only
        self.assertEqual(
            mock_api.method_calls[:2],
            [
                call.get_task_status(self.master_addr, self.task_name, bk_cloud_id=self.bk_cloud_id),
                call.get_task(self.master_addr, self.task_name, bk_cloud_id=self.bk_cloud_id),
            ],
        )
