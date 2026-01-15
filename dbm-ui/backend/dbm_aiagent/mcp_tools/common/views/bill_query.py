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

from backend.dbm_aiagent.mcp_tools.common.serializers.bill_status_tracker import (
    BillStatusTrackerInputSerializer,
    BillStatusTrackerOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketStatus
from backend.ticket.models import FlowSummary, Ticket

logger = logging.getLogger("root")


class BillQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询单据状态")),
        request_slz=BillStatusTrackerInputSerializer,
        response_slz=BillStatusTrackerOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.BILL_QUERY],
        name_prefix="bill_query",
    )
    def bill_status_tracker(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        bill_id = self.get_param("bill_id")

        tk = Ticket.objects.get(bk_biz_id=bk_biz_id, pk=bill_id)

        msgs = [""]
        if tk.status == TicketStatus.SUCCEEDED:
            current_flow = ""
        elif tk.status == TicketStatus.TERMINATED:
            current_flow = ""
            msgs = [tk.get_terminate_reason()]
        else:
            current_flow = tk.current_flow().flow_alias

        if tk.status in [TicketStatus.TERMINATED, TicketStatus.FAILED]:
            msgs = list(
                FlowSummary.objects.filter(flow__ticket=tk, flow__status=TicketStatus.FAILED).values_list(
                    "summary", flat=True
                )
            )

        return Response(
            {
                # "bk_biz_id": bk_biz_id,
                # "bill_id": bill_id,
                "status": tk.status,
                "current_flow": current_flow,
                "cost_time_seconds": tk.get_cost_time(),
                "msgs": msgs,
            }
        )
