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

from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.db_report.enums import ReportStateType
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode
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

    根据flow的不同状态更新MySQLBackupRecoverTask的phase和state：
    - StateType.FAILED/REVOKED: 更新phase为DONE，state为ReportStateType.ABNORMAL
    - StateType.FINISHED: 更新phase为DONE，state保持为空
    - StateType.RUNNING/CREATED/READY: 更新phase为RUNNING

    注意：
    - task_status字段由flow中的MySQLBackupRecoverTaskMetaComponent组件负责更新
    - task_info字段不在此处更新，可通过任务详情查看错误日志
    - state字段一旦设置为ReportStateType.ABNORMAL后，后续不再改变

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

        if status == StateType.FINISHED:
            task.phase = TaskPhase.DONE
            logger.info(_("MySQL备份恢复演练成功完成，task_id={}").format(root_id))

        elif status in [StateType.FAILED, StateType.REVOKED]:
            task.phase = TaskPhase.DONE
            # 备份恢复失败时，设置 state 为 abnormal，且后续不再改变
            if task.task_status != TaskStatus.RECOVER_SUCCESS and task.state != ReportStateType.NORMAL.value:
                task.state = ReportStateType.ABNORMAL.value
                update_fields.append("state")
            logger.warning(_("MySQL备份恢复演练失败，task_id={}, status={}").format(root_id, status))

        # 保存更新
        task.save(update_fields=update_fields)
        logger.info(_("MySQLBackupRecoverTask状态更新成功，task_id={}, phase={}").format(root_id, task.phase))
        if status == StateType.FINISHED:
            _record_exercise_timing(task, root_id, node_id)

    except Exception as e:
        logger.error(_("MySQL备份恢复演练信号处理器执行失败: {}").format(str(e)))
        return


def _positive_seconds(start, end):
    if start is None or end is None or end < start:
        return None
    return int((end - start).total_seconds())


def _clean_finished(root_id: str, node_id: str) -> bool:
    """节点正常完成：排除跳过和忽略错误的完成态"""
    state = BambooEngine(root_id=root_id).get_node_state(node_id)
    if state is None or state.name != StateType.FINISHED:
        return False
    return not (state.skip or state.error_ignored)


def _node_outputs(root_id: str, node_id: str) -> dict:
    try:
        result = BambooEngine(root_id=root_id).get_node_output_data(node_id)
    except Exception as exc:
        logger.warning(_("读取演练步骤输出失败，node_id={}, error={}").format(node_id, exc))
        return {}
    data = getattr(result, "data", None) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _record_exercise_timing(task: MySQLBackupRecoverTask, root_id: str, node_id: str) -> None:
    nodes = task.exercise_timing_nodes if isinstance(task.exercise_timing_nodes, dict) else {}
    download_ids = nodes.get("backup_download_node_ids") or []
    recover_id = nodes.get("recover_node_id") or ""
    if node_id in download_ids:
        _record_backup_download(task, root_id, download_ids)
    if node_id and node_id == recover_id:
        _record_pure_recover(task, root_id, recover_id)


def _record_backup_download(task: MySQLBackupRecoverTask, root_id: str, download_ids: list) -> None:
    """所有下载批次都正常完成后，记录最早开始时间与各批次耗时之和"""
    if not download_ids or task.backup_download_duration is not None:
        return
    if not all(_clean_finished(root_id, download_id) for download_id in download_ids):
        return
    rows = {row.node_id: row for row in FlowNode.objects.filter(root_id=root_id, node_id__in=download_ids)}
    spans = []
    starts = []
    for download_id in download_ids:
        row = rows.get(download_id)
        seconds = _positive_seconds(getattr(row, "started_at", None), getattr(row, "updated_at", None))
        if seconds is None:
            return
        spans.append(seconds)
        starts.append(row.started_at)
    task.backup_download_start_time = min(starts)
    task.backup_download_duration = sum(spans)
    task.save(update_fields=["backup_download_start_time", "backup_download_duration", "update_at"])


def _record_pure_recover(task: MySQLBackupRecoverTask, root_id: str, recover_id: str) -> None:
    """恢复数据步骤成功后，按该步骤自身起止时间记录纯恢复耗时，不依赖下载耗时"""
    if task.recover_duration is not None:
        return
    if not _clean_finished(root_id, recover_id):
        return
    outputs = _node_outputs(root_id, recover_id)
    if outputs.get("rollback_code") != 0 or outputs.get("job_execute") is not True:
        return
    row = FlowNode.objects.filter(root_id=root_id, node_id=recover_id).first()
    seconds = _positive_seconds(getattr(row, "started_at", None), getattr(row, "updated_at", None))
    if seconds is None:
        return
    task.recover_start_time = row.started_at
    task.recover_end_time = row.updated_at
    task.recover_duration = seconds
    task.save(update_fields=["recover_start_time", "recover_end_time", "recover_duration", "update_at"])
