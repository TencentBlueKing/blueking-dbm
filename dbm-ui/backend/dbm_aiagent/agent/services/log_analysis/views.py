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
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.dbm_aiagent.agent.services.log_analysis.serializers import GetLogAnalysisSerializer
from backend.dbm_aiagent.models.ai_log import TicketFlowAILog

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
