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

from django.utils.translation import gettext as _

from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.signal.callback_map import create_ticket_handler
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


# 定义flow状态到MySQLBackupRecoverTask状态的映射
flow_status_to_task_status_map = {
    StateType.FAILED: TaskPhase.DONE,
    StateType.REVOKED: TaskPhase.DONE,
    StateType.FINISHED: TaskPhase.DONE,
    StateType.RUNNING: TaskPhase.RUNNING,
    StateType.CREATED: TaskPhase.RUNNING,
    StateType.READY: TaskPhase.RUNNING,
}


@create_ticket_handler(TicketType.MYSQL_ROLLBACK_EXERCISE)
def mysql_rollback_exercise_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    """
    MySQL备份恢复演练的信号状态处理函数

    根据flow的不同状态更新MySQLBackupRecoverTask的状态：
    - StateType.FAILED: 更新为COMMIT_FAILED
    - StateType.REVOKED: 更新为COMMIT_FAILED
    - StateType.FINISHED: 更新为RECOVER_SUCCESS
    - StateType.RUNNING: 更新为COMMIT_SUCCESS
    - StateType.CREATED/READY: 更新为COMMIT_SUCCESS

    Args:
        root_id: 流程根ID
        node_id: 节点ID
        status: 当前状态
        **kwargs: 其他参数
    """
    logger.info(_("执行MySQL备份恢复演练信号处理器，root_id={}, node_id={}, status={}").format(root_id, node_id, status))

    try:
        # 根据root_id查找对应的MySQLBackupRecoverTask
        task = MySQLBackupRecoverTask.objects.filter(task_id=root_id).first()
        if not task:
            logger.warning(_("未找到对应的MySQLBackupRecoverTask，root_id={}").format(root_id))
            return

        # 获取对应的任务状态
        task_phase = flow_status_to_task_status_map.get(status)
        if not task_phase:
            logger.info(_("状态{}没有对应的任务状态映射，跳过更新").format(status))
            return

        # 更新任务状态
        update_fields = ["update_at", "phase"]
        task.phase = task_phase

        # 如果是恢复成功状态，更新恢复结束时间
        if status == StateType.FINISHED:
            task.status = True  # 设置巡检结果状态为正常
            task.phase = TaskPhase.DONE
            update_fields.extend(["status"])
            logger.info(_("MySQL备份恢复演练成功完成，task_id={}").format(root_id))

        # 如果是失败状态，记录错误信息
        elif status in [StateType.FAILED, StateType.REVOKED]:
            # 尝试从flow engine获取错误信息
            try:
                engine = BambooEngine(root_id=root_id)
                pipeline_states = engine.get_pipeline_states().data
                if root_id in pipeline_states and pipeline_states[root_id].get("error"):
                    task.task_info = pipeline_states[root_id]["error"]
                    update_fields.append("task_info")
            except Exception as e:
                logger.warning(_("获取flow错误信息失败: {}").format(str(e)))

            task.status = False  # 设置巡检结果状态为异常
            task.phase = TaskPhase.DONE
            update_fields.append("status")
            logger.warning(_("MySQL备份恢复演练失败，task_id={}, status={}").format(root_id, status))

        # 保存更新
        task.save(update_fields=update_fields)
        logger.info(
            _("MySQLBackupRecoverTask状态更新成功，task_id={}, 原状态={}, 新状态={}").format(root_id, task.phase, task_phase)
        )

    except Exception as e:
        logger.error(_("MySQL备份恢复演练信号处理器执行失败: {}").format(str(e)))
        return
