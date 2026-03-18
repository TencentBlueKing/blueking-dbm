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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs, auth_parse_ticket_biz
from backend.dbm_aiagent.mcp_tools.common.impl.ticket_list import ticket_list
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_list import (
    TicketListInputSerializer,
    TicketListOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_manipulate import (
    TicketManipulateInputSerializer,
    TicketManipulateOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBadTicketStatusException
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpDBManagePermission
from backend.ticket.constants import TicketStatus
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Ticket
from backend.ticket.todos import TodoActionType

logger = logging.getLogger("root")


class TicketOperationMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""查询单据列表, 每个单据一行返回结果, 单据参数是个 json, 搞的好看点""")),
        request_slz=TicketListInputSerializer,
        response_slz=TicketListOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        mcp=[DBMMcpTools.TICKET_OP, DBMMcpTools.TICKET_OP_MARKET],
        name_prefix="ticket_op",
    )
    def ticket_list(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        # ticket_types = self.get_param("ticket_types")
        ticket_ids = self.get_param("ticket_ids")
        cluster_domains = self.get_param("cluster_domains")
        statuses = self.get_param("statuses")
        time_duration = self.get_param("time_duration")

        # username = request.user.username

        res = ticket_list(bk_biz_id, ticket_ids, cluster_domains, statuses, time_duration)
        # res = ticket_list(username, bk_biz_id, ticket_ids, cluster_domains, statuses, time_duration)
        return Response({"ticket_infos": res})

    @mcp_tools_api_decorator(
        description=str(_("执行单据")),
        request_slz=TicketManipulateInputSerializer,
        response_slz=TicketManipulateOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TICKET_OP],
        mcp_auth_parser=auth_parse_ticket_biz,
        name_prefix="ticket_op",
    )
    def ticket_execute(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        ticket_id = self.get_param("ticket_id")

        username = request.user.username

        tk = Ticket.objects.get(pk=ticket_id)
        if not (username == tk.creator or username in tk.helpers):
            raise DBMMcpBadTicketStatusException(msg=f"用户 {username} 无权限操作该单据")

        if tk.status != TicketStatus.TODO:
            raise DBMMcpBadTicketStatusException(msg=f"{tk.status} 不支持当前操作")

        TicketHandler.batch_process_ticket(
            username=username, action=TodoActionType.APPROVE, ticket_ids=[ticket_id], params={}
        )

        time.sleep(5)  # 这里 sleep 是为了能返回一个正常点的状态

        return Response({"status": Ticket.objects.get(pk=ticket_id).status})

    @mcp_tools_api_decorator(
        description=str(_("终止单据")),
        request_slz=TicketManipulateInputSerializer,
        response_slz=TicketManipulateOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.TICKET_OP],
        mcp_auth_parser=auth_parse_ticket_biz,
        name_prefix="ticket_op",
    )
    def ticket_terminate(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        ticket_id = self.get_param("ticket_id")
        username = request.user.username

        tk = Ticket.objects.get(pk=ticket_id)
        if not (username == tk.creator or username in tk.helpers):
            raise DBMMcpBadTicketStatusException(msg=f"用户 {username} 无权限操作该单据")

        if tk.status in [TicketStatus.RUNNING, TicketStatus.TERMINATED, TicketStatus.INNER_TODO]:
            raise DBMMcpBadTicketStatusException(msg=f"{tk.status} 不支持当前操作")

        TicketHandler.batch_process_ticket(
            username=username, action=TodoActionType.TERMINATE, ticket_ids=[ticket_id], params={}
        )

        time.sleep(5)  # 这里 sleep 是为了能返回一个正常点的状态

        return Response({"status": Ticket.objects.get(pk=ticket_id).status})
