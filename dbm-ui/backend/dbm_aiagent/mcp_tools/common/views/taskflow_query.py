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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.impl.taskflow_error_log import get_taskflow_error_logs
from backend.dbm_aiagent.mcp_tools.common.serializers.taskflow_log_query import (
    FailedTaskflowListInputSerializer,
    FailedTaskflowListOutputSerializer,
    TaskflowErrorLogOutputSerializer,
    TaskflowLogQueryInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class TaskflowQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("根据任务 root_id 查询最后一个失败节点的错误日志")),
        request_slz=TaskflowLogQueryInputSerializer,
        response_slz=TaskflowErrorLogOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TASKFLOW_QUERY],
        name_prefix="taskflow_query",
    )
    def get_taskflow_error_logs(self, request, *args, **kwargs):
        root_id = self.get_param("root_id")
        result = get_taskflow_error_logs(root_id)
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("根据日期范围和单据类型查询失败的任务流 root_id 列表")),
        request_slz=FailedTaskflowListInputSerializer,
        response_slz=FailedTaskflowListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TASKFLOW_QUERY],
        name_prefix="taskflow_query",
    )
    def list_failed_taskflow(self, request, *args, **kwargs):
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        ticket_types = self.get_param("ticket_types")

        qs = FlowTree.objects.filter(
            status=StateType.FAILED,
            created_at__gte=start_time,
            created_at__lte=end_time,
        )
        if ticket_types:
            qs = qs.filter(ticket_type__in=ticket_types)

        root_ids = list(qs.values_list("root_id", flat=True))
        return Response({"root_ids": root_ids})
