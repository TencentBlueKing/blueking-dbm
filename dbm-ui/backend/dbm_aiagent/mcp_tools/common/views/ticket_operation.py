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
import time

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.impl.ticket_list import ticket_list
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_execute import (
    TicketExecuteInputSerializer,
    TicketExecuteOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_list import (
    TicketListInputSerializer,
    TicketListOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_status_tracker import (
    BillStatusTrackerInputSerializer,
    BillStatusTrackerOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBadTicketStatusException
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketStatus
from backend.ticket.handler import TicketHandler
from backend.ticket.models import FlowSummary, Ticket

logger = logging.getLogger("root")


class TicketOperationMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询单据列表
        按 ID, 类型, 状态, 关联集群, 创建时间
        每个单据一行返回结果"""
            )
        ),
        request_slz=TicketListInputSerializer,
        response_slz=TicketListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TICKET_OP],
        name_prefix="ticket_op",
    )
    def ticket_list(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        # ticket_types = self.get_param("ticket_types")
        ticket_ids = self.get_param("ticket_ids")
        cluster_domains = self.get_param("cluster_domains")
        statuses = self.get_param("statuses")
        time_duration = self.get_param("time_duration")

        username = request.user.username

        res = ticket_list(username, bk_biz_id, ticket_ids, cluster_domains, statuses, time_duration)
        return Response({"bill_infos": res})

    @mcp_tools_api_decorator(
        description=str(_("执行单据")),
        request_slz=TicketExecuteInputSerializer,
        response_slz=TicketExecuteOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TICKET_OP],
        name_prefix="ticket_op",
    )
    def ticket_execute(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        ticket_id = self.get_param("ticket_id")

        username = request.user.username

        tk = Ticket.objects.get(bk_biz_id=bk_biz_id, pk=ticket_id)
        if tk.status != TicketStatus.TODO:
            raise DBMMcpBadTicketStatusException(msg=f"{tk.status} 不支持当前操作")

        TicketHandler.batch_process_ticket(username=username, action="approve", ticket_ids=[ticket_id], params={})

        time.sleep(5)  # 这里 sleep 是为了能返回一个正常点的状态

        return Response({"status": Ticket.objects.get(bk_biz_id=bk_biz_id, pk=ticket_id).status})

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询单据的详情
        params 是一个 json 结构, 输出的时候格式化的好看点
        """
            )
        ),
        request_slz=BillStatusTrackerInputSerializer,
        response_slz=BillStatusTrackerOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TICKET_OP],
        name_prefix="ticket_op",
    )
    def ticket_tracker(self, request, *args, **kwargs):
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
                "status": tk.status,
                "creator": tk.creator,
                "created_at": tk.create_at,
                "params": tk.details,
                "current_flow": current_flow,
                "cost_time_seconds": tk.get_cost_time(),
                "msgs": msgs,
            }
        )
