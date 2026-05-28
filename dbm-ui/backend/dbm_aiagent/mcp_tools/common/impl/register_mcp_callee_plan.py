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
from backend import env
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.models.mcp_callee_plan import McpCalleePlan
from backend.ticket.builders.common.mcp_callee_plan import RegisterMcpCalleePlanDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def register_mcp_callee_plan(callee_plan: McpCalleePlan, username: str, ticket_type: TicketType) -> Ticket:
    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
        "details": {
            "plan_id": callee_plan.pk,
            "mcp_id": callee_plan.callee_mcp_id,
            "params": callee_plan.params,
            "time_window_start": callee_plan.time_window_start.isoformat(),
            "time_window_end": callee_plan.time_window_end.isoformat(),
            "max_call_count": callee_plan.max_call_count,
        },
    }

    slz = RegisterMcpCalleePlanDetailSerializer(data=ticket_param["details"])
    slz.context["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    slz.context["ticket_type"] = TicketType.MYSQL_REGISTER_MCP_CALLEE_PLAN
    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
