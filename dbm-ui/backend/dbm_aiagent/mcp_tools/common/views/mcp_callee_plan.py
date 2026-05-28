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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.configuration.constants import DBType
from backend.dbm_aiagent.mcp_tools.common.impl.register_mcp_callee_plan import register_mcp_callee_plan
from backend.dbm_aiagent.mcp_tools.common.serializers.mcp_callee_plan import RegisterCalleePlanInputSerializer
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import MCP_TOOLS_REGISTRY, mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpCalleePlanException
from backend.dbm_aiagent.mcp_tools.mysql.serializers.bill_output import SubmitBillOutputSerializer
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.dbm_aiagent.models.mcp_callee_plan import McpCalleePlan
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType


class McpCalleePlanMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("注册 mcp callee 计划")),
        request_slz=RegisterCalleePlanInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.DBM],
        name_prefix="mcp_callee_plan",
        permission_classes=[],
        mcp_auth_parser=None,
    )
    def register_mcp_callee_plan(self, request, *args, **kwargs):
        all_operation_ids = {op_id for op_ids in MCP_TOOLS_REGISTRY.values() for op_id in op_ids}
        if self.get_param("callee_mcp_id") not in all_operation_ids:
            raise DBMMcpCalleePlanException(msg=f"{self.get_param('callee_mcp_id')} not found")

        db_type = self.get_param("db_type")
        if db_type in [DBType.MySQL.value, DBType.TenDBCluster.value]:
            ticket_type = TicketType.MYSQL_REGISTER_MCP_CALLEE_PLAN
        else:
            raise DBMMcpCalleePlanException(msg=f"{db_type} not implement register mcp plan ticket yet")

        callee_plan = McpCalleePlan.objects.create(
            username=request.user.username,
            callee_mcp_id=self.get_param("callee_mcp_id"),
            params=self.get_param("params"),
            time_window_start=self.get_param("time_window_start"),
            time_window_end=self.get_param("time_window_end"),
            max_call_count=self.get_param("max_call_count"),
        )

        return Response(register_mcp_callee_plan(callee_plan, request.user.username, ticket_type))
