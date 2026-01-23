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

from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


def ticket_list(
    username: str,
    bk_biz_id: int,
    ticket_ids: List[int],
    want_cluster_domains: List[str],
    statuses: List[TicketStatus],
    time_duration: timedelta,
):
    q = Q(**{"bk_biz_id": bk_biz_id, "create_at__gte": timezone.now() - time_duration})

    if ticket_ids:
        q &= Q(**{"pk__in": ticket_ids})
    if statuses:
        q &= Q(**{"status__in": statuses})

    # want_cluster_ids = []
    # if cluster_domains:
    #     want_cluster_ids = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domains).values_list(
    #         'pk', flat=True)

    want_tickets = []
    for t in Ticket.objects.filter(q):
        creator = t.creator
        helpers = t.helpers
        if not (username == creator or username in helpers):
            continue

        # if 'clusters' in t.details:
        #     relate_cluster_do = list(t.details['clusters'].keys())
        # else:
        #     relate_cluster_ids = []

        relate_cluster_domains = [v["immute_domain"] for k, v in t.details.get("clusters", {}).items()]

        if want_cluster_domains:  # 这里要保持这样, 当输入的域名实际不对时, 就不会返回东西
            if bool(set(relate_cluster_domains) & set(want_cluster_domains)):
                want_tickets.append(
                    {
                        "ticket_id": t.pk,
                        "ticket_type": TicketType.get_choice_label(t.ticket_type),
                        "creator": creator,
                        "helpers": helpers[:2],
                        "status": t.status,
                        "relate_clusters": "\n".join(relate_cluster_domains),
                        "created_at": t.create_at,
                        # "bill_param": __rebuild_ticket_param(t)
                    }
                )
        else:
            want_tickets.append(
                {
                    "ticket_id": t.pk,
                    "ticket_type": TicketType.get_choice_label(t.ticket_type),
                    "creator": creator,
                    "helpers": helpers[:2],
                    "status": t.status,
                    "relate_clusters": "\n".join(relate_cluster_domains),
                    "created_at": t.create_at,
                    # "bill_param": __rebuild_ticket_param(t)
                }
            )

    return want_tickets


def __rebuild_ticket_param(tk: Ticket):
    if tk.status not in [TicketStatus.TODO, TicketStatus.APPROVE]:
        return ""
    # return tk.details
    # logger.info(tk.pk)
    #
    ticket_type = tk.ticket_type
    ticket_serializer_class = BuilderFactory.get_serializer(ticket_type).__class__
    slz = ticket_serializer_class(data=tk.details)
    slz.context.update({"ticket_type": ticket_type})
    slz.context.update({"bk_biz_id": tk.bk_biz_id})
    try:
        slz.is_valid(raise_exception=False)
        return slz.validated_data
    except Exception as e:
        logger.info(f"{e}: {tk}")

    return ""
