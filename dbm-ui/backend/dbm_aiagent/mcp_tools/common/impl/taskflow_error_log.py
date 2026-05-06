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
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.bk_web.constants import LogLevelName
from backend.db_periodic_task.models import MySQLBackupRecoverTask
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


def _collect_node_names(activities: Dict, name_map: Dict) -> None:
    """递归收集所有节点名称到 name_map。"""
    for node_id, activity in activities.items():
        name_map[node_id] = activity.get("name", "")
        if "pipeline" in activity:
            _collect_node_names(activity["pipeline"].get("activities", {}), name_map)


def get_taskflow_error_logs(root_id: str) -> Dict:
    """
    根据任务流 root_id 查询最后一个失败节点的错误日志。

    通过 FlowNode 表（按 updated_at 降序）直接定位最后失败的节点，
    节点名称从 FlowTree.tree 中取，均为 root_id 索引/PK 查询，无全表扫描。
    """
    # 按 updated_at 降序取最后失败的节点（root_id 有索引）
    last_failed = FlowNode.objects.filter(root_id=root_id, status=StateType.FAILED).order_by("-updated_at").first()
    if not last_failed:
        logs: List = []
        _append_mysql_rollback_exercise_task_info_to_logs(root_id, logs)
        return {"node_id": "", "node_name": "", "logs": logs}

    node_id = last_failed.node_id
    version_id = last_failed.version_id

    # 从 FlowTree（PK 查询）中取节点名称
    node_name = ""
    engine = BambooEngine(root_id=root_id)
    tree = engine.get_pipeline_tree()
    if tree:
        name_map: Dict = {}
        _collect_node_names(tree.get("activities", {}), name_map)
        node_name = name_map.get(node_id, "")

    handler = TaskFlowHandler(root_id=root_id)
    logs = handler.get_version_error_logs_for_dbactuator(node_id=node_id, version_id=version_id)
    _append_mysql_rollback_exercise_task_info_to_logs(root_id, logs)

    return {"node_id": node_id, "node_name": node_name, "logs": logs}


def _append_mysql_rollback_exercise_task_info_to_logs(root_id: str, logs: List) -> None:
    """若为 MYSQL_ROLLBACK_EXERCISE，将 MySQLBackupRecoverTask.task_info 追加为一条错误日志。"""
    flow = FlowTree.objects.filter(root_id=root_id).only("ticket_type").first()
    if not flow or flow.ticket_type != TicketType.MYSQL_ROLLBACK_EXERCISE.value:
        return
    recover = MySQLBackupRecoverTask.objects.filter(task_id=root_id).only("task_info").first()
    if not recover or not recover.task_info:
        return
    logs.append(
        TaskFlowHandler.generate_log_record(
            message=_("备份恢复演练任务信息(task_info):\n{}").format(recover.task_info),
            levelname=LogLevelName.ERROR.value,
        )
    )
