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

from celery import shared_task

from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.dbm_aiagent.agent.commands import TicketFlowLogAnalysisCommand
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.ticket.constants import TicketType
from backend.ticket.models import Flow, Ticket

logger = logging.getLogger("root")


@shared_task
def pipeline_log_ai_analysis(root_id: str = None) -> List[Dict]:
    """
    流程日志AI分析
    @param root_id
    """
    from backend.dbm_aiagent.models.ai_log import TicketFlowAILog

    handler = TaskFlowHandler(root_id=root_id)
    ticket_id = int(FlowTree.objects.get(root_id=root_id).uid or 0)
    ticket = Ticket.objects.filter(id=ticket_id).first()
    ticket_type = ticket.ticket_type if ticket else ""
    node_ids = handler.get_specific_node_ids(status=StateType.FAILED)

    if not node_ids:
        logger.info(f"pipeline {root_id} doesn't have failed nodes")
        return []

    # 节点版本映射
    node_version_map = {
        f.node_id: f.version_id for f in FlowNode.objects.filter(root_id=root_id, node_id__in=node_ids)
    }
    # 节点名称映射
    node_name_map = {}
    engine = BambooEngine(root_id=root_id)
    engine.recursion_activity_name(engine.get_pipeline_tree()["activities"], node_name_map)

    error_logs = []
    for node_id in node_ids:
        # 从日志平台获取节点日志
        logs = handler.get_version_logs(node_id, node_version_map[node_id])
        if not logs:
            continue

        # 格式化错误日志
        error_messages = [f"[{log['levelname']}] {log['message']}" for log in logs]
        error_logs.append({"component": node_name_map[node_id], "error_msg": "\n".join(error_messages), "context": {}})

    result = AgentHandler.ask_agent_with_command(
        command=TicketFlowLogAnalysisCommand.command,
        command_params={"log_content": error_logs, "ticket_type": ticket_type},
    )
    TicketFlowAILog.objects.update_or_create(ticket_id=ticket_id, flow_obj_id=root_id, defaults={"ai_summary": result})


@shared_task
def ticket_flow_log_ai_analysis(flow_id: str):
    """
    工单流程日志AI分析
    @param flow_id: 单据流程ID
    """
    from backend.dbm_aiagent.models.ai_log import TicketFlowAILog

    flow = Flow.objects.get(flow_obj_id=flow_id)
    ticket_id = flow.ticket_id
    if not flow.err_msg:
        return

    error_logs = {
        "component": str(TicketType.get_choice_label(flow.ticket.ticket_type)),
        "error_msg": flow.err_msg,
        "context": {},
    }
    result = AgentHandler.ask_agent_with_command(
        command=TicketFlowLogAnalysisCommand.command,
        command_params={"log_content": error_logs, "ticket_type": flow.ticket.ticket_type},
    )
    TicketFlowAILog.objects.update_or_create(ticket_id=ticket_id, flow_obj_id=flow_id, defaults={"ai_summary": result})
