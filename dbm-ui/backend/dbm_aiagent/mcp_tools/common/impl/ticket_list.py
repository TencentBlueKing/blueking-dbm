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
from datetime import timedelta
from typing import List

from django.db.models import Q
from django.utils import timezone

from backend.dbm_aiagent.apps import TICKET_SCHEMA
from backend.dbm_aiagent.mcp_tools.common.helps.extract_ticket_info_by_schema.extracter import extract_by_schema
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import FlowSummary, Ticket

logger = logging.getLogger("root")


def ticket_list(
    # username: str,
    bk_biz_id: int,
    ticket_ids: List[int],
    want_cluster_domains: List[str],
    statuses: List[TicketStatus],
    time_duration: timedelta,
):
    q = Q(**{"create_at__gte": timezone.now() - time_duration})

    if bk_biz_id:
        q &= Q(**{"bk_biz_id": bk_biz_id})

    if ticket_ids:
        q &= Q(**{"pk__in": ticket_ids})

    if statuses:
        q &= Q(**{"status__in": statuses})

    # want_cluster_ids = []
    # if cluster_domains:
    #     want_cluster_ids = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domains).values_list(
    #         'pk', flat=True)

    want_tickets = []
    tickets_qs = Ticket.objects.prefetch_related("flows", "todo_of_ticket").filter(q)
    for t in tickets_qs:
        creator = t.creator
        helpers = t.helpers
        # if not (username == creator or username in helpers):
        #     continue

        msgs = [""]
        if t.status == TicketStatus.SUCCEEDED:
            current_flow = ""
        elif t.status == TicketStatus.TERMINATED:
            current_flow = ""
            msgs = [t.get_terminate_reason()]
        else:
            current_flow = t.current_flow().flow_alias

        if t.status in [TicketStatus.TERMINATED, TicketStatus.FAILED]:
            msgs = list(
                FlowSummary.objects.filter(flow__ticket=t, flow__status=TicketStatus.FAILED).values_list(
                    "summary", flat=True
                )
            )
        relate_cluster_domains = [v["immute_domain"] for k, v in t.details.get("clusters", {}).items()]

        include_want_cluster_domains = bool(set(relate_cluster_domains) & set(want_cluster_domains))
        if not want_cluster_domains or (want_cluster_domains and include_want_cluster_domains):
            want_tickets.append(
                {
                    "ticket_id": t.pk,
                    "ticket_type": TicketType.get_choice_label(t.ticket_type),
                    "creator": creator,
                    "helpers": helpers[:2],
                    "status": t.status,
                    "relate_clusters": "\n".join(relate_cluster_domains),
                    "created_at": t.create_at,
                    "ticket_param": rebuild_ticket_param(t),
                    "current_flow": current_flow,
                    "todos": get_ticket_todos(t),
                    "cost_time_seconds": t.get_cost_time(),
                    "msgs": msgs,
                }
            )

    return want_tickets


def rebuild_ticket_param(tk: Ticket):
    ticket_type = tk.ticket_type
    if ticket_type in TICKET_SCHEMA:
        ticket_schema = TICKET_SCHEMA[ticket_type]
        details_schema = ticket_schema.get("properties", {}).get("details", {})
        if "properties" not in details_schema:
            return ""

        try:
            data = extract_by_schema(details_schema, tk.details)
            return data
        except Exception as e:
            logger.error(f"extract_by_schema error: {e}")
            raise e
    else:
        return ""


def get_ticket_todos(tk: Ticket):
    todos = [
        {
            "todo_id": todo.id,
            "todo_type": todo.type,
            "name": todo.name,
            "operators": todo.operators,
            "helpers": todo.helpers,
        }
        for todo in tk.todo_of_ticket.all()
    ]
    return todos
