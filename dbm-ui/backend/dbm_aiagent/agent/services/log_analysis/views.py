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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.constants import LogLabel
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.dbresource.client import DBResourceApi
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.dbm_aiagent.agent.services.log_analysis.serializers import (
    GetLogAnalysisSerializer,
    GetNodeLogAnalysisSerializer,
)
from backend.dbm_aiagent.models.ai_log import TicketFlowAILog
from backend.env import DEFAULT_USERNAME
from backend.flow.models import FlowNode
from backend.ticket.models import Ticket

logger = logging.getLogger("root")
SWAGGER_TAG = _("AI日志分析")


class AILogAnalysisViewSet(viewsets.SystemViewSet):
    """AI日志分析视图集"""

    default_permission_class = []

    @common_swagger_auto_schema(
        operation_summary=_("获取单据流程日志分析"),
        request_body=GetLogAnalysisSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetLogAnalysisSerializer)
    def get_flow_log_analysis(self, request):
        """获取单据流程日志分析"""
        params = self.params_validate(self.get_serializer_class())
        try:
            log = TicketFlowAILog.objects.get(ticket_id=params["ticket_id"], flow_obj_id=params["flow_id"]).ai_summary
        except TicketFlowAILog.DoesNotExist:
            log = _("暂无 AI 分析结果，如需排查错误，请先查阅原始日志。")
        return Response(log)

    @common_swagger_auto_schema(
        operation_summary=_("获取节点日志AI分析"),
        request_body=GetNodeLogAnalysisSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetNodeLogAnalysisSerializer)
    def get_node_log_analysis(self, request):
        """获取节点日志AI分析(流式)"""
        params = self.params_validate(self.get_serializer_class())
        node_id = params["node_id"]
        command = params["command"]

        # 获取节点和单据信息
        flow_node = FlowNode.objects.filter(node_id=node_id).order_by("-updated_at").first()
        if not flow_node:
            return Response(_("节点不存在"))
        ticket = Ticket.objects.filter(id=flow_node.uid).first()
        ticket_type = ticket.ticket_type if ticket else ""

        # 获取节点日志，过滤掉AI不关注的
        logs = TaskFlowHandler(root_id=flow_node.root_id).get_version_logs(
            node_id, flow_node.version_id, label_filters=[LogLabel.NOT_AI]
        )
        ai_log_content = "\n".join([f"[{log.get('levelname')}] {log.get('message')}" for log in logs])
        command_params = {"log_content": ai_log_content, "ticket_type": ticket_type}

        # 获取AI分析结果
        username = getattr(request.user, "username", None) or DEFAULT_USERNAME
        res = AgentHandler.ask_agent_with_command(
            command=command, command_params=command_params, username=username, stream=True
        )

        return res

    @common_swagger_auto_schema(
        operation_summary=_("获取单据缺货日志AI分析"),
        request_body=GetLogAnalysisSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetLogAnalysisSerializer)
    def get_resource_lack_log_analysis(self, request):
        """获取单据缺货日志AI分析"""
        params = self.params_validate(self.get_serializer_class())
        try:
            lack_log = DBResourceApi.resource_lack_analysis(params={"bill_id": params["ticket_id"]})["markdown_text"]
        except Exception as e:  # pylint: disable=broad-except
            logger.error(_("获取单据缺货日志AI分析失败: {}").format(e))
            lack_log = _("暂无 AI 分析结果，如需排查错误，请先查阅原始日志。")
        return Response(lack_log)
