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
from collections import OrderedDict
from typing import List, Optional, Union

from django.utils.translation import gettext as _

from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket

logger = logging.getLogger("flow")


def _format_deferred_targets(infos: list) -> str:
    """单据备注里的下架目标：按 IP 去重（延迟下架针对整机，不写端口）。"""
    ips: OrderedDict = OrderedDict()
    for info in infos or []:
        ip = info.get("ip") or ""
        if ip:
            ips[ip] = None
    return ";".join(ips.keys())


def _unlock_running_for_deferred(running_ticket: Ticket, infos: list) -> None:
    """
    替换/自愈单仍 RUNNING 时出延迟下架会撞集群互斥；
    先对**正在跑的单**操作记录解锁 MONGODB_DEFERRED_DEINSTALL。
    """
    unlock_types = [TicketType.MONGODB_DEFERRED_DEINSTALL.value]
    cluster_ids: List[int] = []
    for info in infos or []:
        cid = info.get("cluster_id")
        if cid:
            cluster_ids.append(int(cid))
    qs = ClusterOperateRecord.objects.filter(ticket_id=running_ticket.id)
    if cluster_ids:
        qs = qs.filter(cluster_id__in=cluster_ids)
    for record in qs:
        record.unlock_ticket_type_operations(unlock_types)
        logger.info(
            "deferred deinstall unlock cluster=%s for %s on running=%s",
            record.cluster_id,
            unlock_types,
            running_ticket.id,
        )


def _resolve_relate_ticket(running_ticket: Ticket) -> Ticket:
    """
    关联展示挂到 PRE：AUTOFIX/RELOAD 与延迟下架都作为 PRE 的子单，避免 PRE→AUTOFIX→DEFERRED 递归链。
    查不到 Core/PRE 时回退挂到 running 单。
    """
    from backend.db_services.mongodb.autofix.models import MongoAutofixCore

    core = MongoAutofixCore.objects.filter(ticket_id=running_ticket.id).order_by("-id").first()
    if not core or not core.pre_ticket_id or core.pre_ticket_id <= 0:
        return running_ticket
    try:
        return Ticket.objects.get(id=core.pre_ticket_id)
    except Ticket.DoesNotExist:
        logger.warning(
            "deferred deinstall pre ticket missing id=%s, relate to running=%s",
            core.pre_ticket_id,
            running_ticket.id,
        )
        return running_ticket


def _resolve_autofix_core_id(running_ticket: Optional[Ticket]) -> int:
    """从运行中的替换/自愈单或 PRE 反查 MongoAutofixCore.id。"""
    if running_ticket is None:
        return 0
    from backend.db_services.mongodb.autofix.models import MongoAutofixCore

    core = MongoAutofixCore.objects.filter(ticket_id=running_ticket.id).order_by("-id").first()
    if core:
        return core.id
    core = MongoAutofixCore.objects.filter(pre_ticket_id=running_ticket.id).order_by("-id").first()
    return core.id if core else 0


def deferred_deinstall_ticket(
    infos: list,
    creator: str,
    bk_biz_id: int,
    parent_ticket: Optional[Union[int, Ticket]] = None,
    poll_interval_sec: int = 300,
    max_wait_hours: int = 168,
) -> Ticket:
    """
    创建 MongoDB 延迟下架单据。

    parent_ticket: 当前正在执行的替换/自愈单（用于互斥解锁）；关联展示优先挂到其对应 PRE。
    """
    from backend.db_services.mongodb.autofix.remark import autofix_core_tag

    running_ticket = parent_ticket
    if running_ticket is not None and isinstance(running_ticket, int):
        running_ticket = Ticket.objects.get(id=running_ticket)

    if running_ticket is not None:
        _unlock_running_for_deferred(running_ticket, infos)

    details = {
        "infos": infos,
        "poll_interval_sec": poll_interval_sec,
        "max_wait_hours": max_wait_hours,
    }
    targets = _format_deferred_targets(infos) or ((infos[0].get("ip") if infos else "") or "unknown")
    core_tag = autofix_core_tag(_resolve_autofix_core_id(running_ticket))
    remark = _("自动发起-延迟下架-{}{}".format(targets, core_tag))
    relate_ticket = None
    if running_ticket is not None:
        relate_ticket = _resolve_relate_ticket(running_ticket)
        # 备注只挂关联根单（优先 PRE），自愈# 已能串起整条链路
        remark = _("自动发起-延迟下架-{}{}-来自单据#{}".format(targets, core_tag, relate_ticket.id))

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_DEFERRED_DEINSTALL.value,
        creator=creator,
        bk_biz_id=bk_biz_id,
        remark=remark,
        details=details,
    )
    if relate_ticket is not None:
        relate_ticket.add_related_ticket(ticket, done=True)
        logger.info(
            "deferred deinstall related ticket=%s under relate=%s (running=%s)",
            ticket.id,
            relate_ticket.id,
            running_ticket.id,
        )
    return ticket
