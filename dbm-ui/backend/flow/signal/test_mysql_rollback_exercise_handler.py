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
import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.flow.consts import StateType
from backend.flow.signal.callback_map import TICKET_TYPE_HANDLERS
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TestMySQLRollbackExerciseHandler(TestCase):
    """测试MySQL备份恢复演练信号处理器"""

    def setUp(self):
        """测试前准备"""
        # 创建测试任务
        self.test_task = MySQLBackupRecoverTask.objects.create(
            bk_biz_id=1,
            cluster_id=1,
            cluster_domain="test.cluster.com",
            cluster_type="TenDBHA",
            backup_id="test_backup_001",
            backup_begin_time=timezone.now(),
            backup_end_time=timezone.now(),
            task_id="test_root_id_001",
            task_status=TaskStatus.COMMIT_SUCCESS,
            phase=TaskPhase.RUNNING,
            status=False,  # 默认异常状态
            creator="test_user",
            updater="test_user",
        )

    def test_handler_registration(self):
        """测试信号处理器是否正确注册"""
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        self.assertIsNotNone(handler, _("MySQL备份恢复演练信号处理器未正确注册"))

    @patch("backend.flow.signal.mysql_rollback_exercise_handler.BambooEngine")
    def test_failed_status_update(self, mock_engine):
        """测试失败状态更新"""
        # 模拟BambooEngine返回错误信息
        mock_engine_instance = MagicMock()
        mock_engine_instance.get_pipeline_states.return_value.data = {"test_root_id_001": {"error": _("测试错误信息")}}
        mock_engine.return_value = mock_engine_instance

        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FAILED)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertEqual(self.test_task.task_info, _("测试错误信息"))
        self.assertFalse(self.test_task.status)  # 巡检结果状态为异常

    @patch("backend.flow.signal.mysql_rollback_exercise_handler.BambooEngine")
    def test_revoked_status_update(self, mock_engine):
        """测试撤销状态更新"""
        # 模拟BambooEngine返回错误信息
        mock_engine_instance = MagicMock()
        mock_engine_instance.get_pipeline_states.return_value.data = {"test_root_id_001": {"error": _("任务被撤销")}}
        mock_engine.return_value = mock_engine_instance

        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.REVOKED)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertEqual(self.test_task.task_info, _("任务被撤销"))
        self.assertFalse(self.test_task.status)  # 巡检结果状态为异常

    def test_finished_status_update(self):
        """测试完成状态更新"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FINISHED)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertTrue(self.test_task.status)  # 巡检结果状态为正常
        self.assertIsNotNone(self.test_task.recover_end_time)

    def test_running_status_update(self):
        """测试运行状态更新"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.RUNNING)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

    def test_created_status_update(self):
        """测试创建状态更新"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.CREATED)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

    def test_ready_status_update(self):
        """测试准备状态更新"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.READY)

        # 验证任务状态更新
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

    def test_task_not_found(self):
        """测试任务不存在的情况"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        # 使用不存在的root_id
        handler(root_id="non_existent_root_id", node_id="test_node_001", status=StateType.FAILED)

        # 验证原任务状态未改变
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

    def test_unknown_status(self):
        """测试未知状态的处理"""
        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        # 使用未知状态
        handler(root_id="test_root_id_001", node_id="test_node_001", status="UNKNOWN_STATUS")

        # 验证任务状态未改变
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

    @patch("backend.flow.signal.mysql_rollback_exercise_handler.BambooEngine")
    def test_engine_exception_handling(self, mock_engine):
        """测试BambooEngine异常处理"""
        # 模拟BambooEngine抛出异常
        mock_engine_instance = MagicMock()
        mock_engine_instance.get_pipeline_states.side_effect = Exception(_("引擎连接失败"))
        mock_engine.return_value = mock_engine_instance

        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FAILED)

        # 验证任务状态更新（即使引擎异常，状态仍应更新）
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertFalse(self.test_task.status)  # 巡检结果状态为异常

    def test_multiple_status_transitions(self):
        """测试多次状态转换"""
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())

        # 从运行到完成
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.RUNNING)
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.RUNNING)

        # 从完成到失败（这种情况不应该发生，但测试处理器行为）
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FINISHED)
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertTrue(self.test_task.status)

    def test_task_fields_preservation(self):
        """测试任务其他字段保持不变"""
        original_create_at = self.test_task.create_at
        original_update_at = self.test_task.update_at
        original_bk_biz_id = self.test_task.bk_biz_id
        original_cluster_id = self.test_task.cluster_id

        # 获取处理器并执行
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FINISHED)

        # 验证任务状态更新
        self.test_task.refresh_from_db()

        # 验证关键字段保持不变
        self.assertEqual(self.test_task.create_at, original_create_at)
        self.assertEqual(self.test_task.bk_biz_id, original_bk_biz_id)
        self.assertEqual(self.test_task.cluster_id, original_cluster_id)
        # update_at应该被更新
        self.assertGreater(self.test_task.update_at, original_update_at)

    def test_handler_with_kwargs(self):
        """测试处理器处理额外参数"""
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_ROLLBACK_EXERCISE.lower())

        # 传递额外参数
        extra_kwargs = {"extra_param": "test_value", "another_param": 123}
        handler(root_id="test_root_id_001", node_id="test_node_001", status=StateType.FINISHED, **extra_kwargs)

        # 验证任务状态更新（处理器应该忽略额外参数）
        self.test_task.refresh_from_db()
        self.assertEqual(self.test_task.phase, TaskPhase.DONE)
        self.assertTrue(self.test_task.status)
