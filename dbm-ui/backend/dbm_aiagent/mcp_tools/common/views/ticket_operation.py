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

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_ticket_biz
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
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBadTicketStatusException, DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.typing import BizIdList
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

    @staticmethod
    def ticket_list_auth_helper(request: HttpRequest, *args, **kwargs) -> BizIdList:
        from backend.db_meta.models import Cluster
        from backend.ticket.models import Ticket

        data = request.query_params if request.method == "GET" else request.data

        if data.get("bk_biz_id"):
            return [data.get("bk_biz_id")]

        if data.get("cluster_domains"):
            cluster_domains = data.get("cluster_domains")
            cluster_domains = cluster_domains if isinstance(cluster_domains, list) else [cluster_domains]
            return list(
                Cluster.objects.filter(immute_domain__in=cluster_domains)
                .values_list("bk_biz_id", flat=True)
                .distinct()
            )

        ticket_ids = data.get("ticket_ids")
        if ticket_ids:
            ticket_ids = ticket_ids if isinstance(ticket_ids, list) else [ticket_ids]
            biz_ids = list(Ticket.objects.filter(id__in=ticket_ids).values_list("bk_biz_id", flat=True).distinct())
            return biz_ids

        raise DBMMcpBaseException(msg="bk_biz_id, ticket_ids and cluster_domains must input at least 1")

    @mcp_tools_api_decorator(
        description=str(_("""查询单据列表, 每个单据一行返回结果, 单据参数是个 json, 搞的好看点""")),
        request_slz=TicketListInputSerializer,
        response_slz=TicketListOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=ticket_list_auth_helper,
        mcp=[DBMMcpTools.TICKET_OP, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="ticket_op",
    )
    def ticket_list(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        ticket_ids = self.get_param("ticket_ids")
        cluster_domains = self.get_param("cluster_domains")
        statuses = self.get_param("statuses")
        time_duration = self.get_param("time_duration")

        if bk_biz_id is None and len(ticket_ids) == 0 and len(cluster_domains) == 0:
            raise DBMMcpBaseException(msg="bk_biz_id, ticket_ids and cluster_domains must input at least 1")

        res = ticket_list(bk_biz_id, ticket_ids, cluster_domains, statuses, time_duration)
        return Response({"ticket_infos": res})

    @mcp_tools_api_decorator(
        description=str(_("执行单据")),
        request_slz=TicketManipulateInputSerializer,
        response_slz=TicketManipulateOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
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
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
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
