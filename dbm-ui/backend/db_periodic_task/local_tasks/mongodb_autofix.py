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

from celery.schedules import crontab

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_services.mongodb.autofix.discover import discover_mongod_backend_faults
from backend.db_services.mongodb.autofix.enums import (
    MONGO_AUTOFIX_ACTIVE_STATUSES,
    MongoAutofixLogEvent,
    MongoAutofixStatus,
)
from backend.db_services.mongodb.autofix.log import write_autofix_log
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("root")

_TICKET_SUCCESS = {TicketStatus.SUCCEEDED.value}
_TICKET_FAIL = {
    TicketStatus.FAILED.value,
    TicketStatus.REVOKED.value,
    TicketStatus.TERMINATED.value,
}
_TICKET_RUNNING = {
    TicketStatus.PENDING.value,
    TicketStatus.APPROVE.value,
    TicketStatus.TODO.value,
    TicketStatus.RESOURCE_REPLENISH.value,
    TicketStatus.TIMER.value,
    TicketStatus.RUNNING.value,
}


def _sync_core_from_tickets(core: MongoAutofixCore) -> None:
    """根据 pre_ticket_id / ticket_id 回写 deal_status."""
    update_fields = ["deal_status", "status_version", "update_at"]
    old_status = core.deal_status

    # 优先盯后续修复/替换单
    if core.ticket_id and core.ticket_id > 0:
        try:
            ticket = Ticket.objects.get(id=core.ticket_id)
        except Ticket.DoesNotExist:
            logger.warning("mongo autofix ticket missing id=%s core=%s", core.ticket_id, core.id)
            return
        if ticket.status in _TICKET_SUCCESS:
            core.deal_status = MongoAutofixStatus.SUCCESS.value
        elif ticket.status in _TICKET_FAIL:
            core.deal_status = MongoAutofixStatus.FAIL.value
            core.status_version = ticket.status
        elif ticket.status in _TICKET_RUNNING:
            if core.deal_status in (
                MongoAutofixStatus.TICKETED.value,
                MongoAutofixStatus.PRE_RUNNING.value,
                MongoAutofixStatus.DETECTED.value,
            ):
                core.deal_status = MongoAutofixStatus.RUNNING.value
        core.save(update_fields=update_fields)
        if core.deal_status != old_status:
            write_autofix_log(
                MongoAutofixLogEvent.STATUS,
                f"status {old_status} -> {core.deal_status} via ticket={ticket.id}({ticket.status})",
                core=core,
                context={"ticket_status": ticket.status, "old_status": old_status},
            )
        return

    # 尚无后续单：盯 PRE
    if core.pre_ticket_id and core.pre_ticket_id > 0:
        try:
            pre = Ticket.objects.get(id=core.pre_ticket_id)
        except Ticket.DoesNotExist:
            logger.warning("mongo autofix pre ticket missing id=%s core=%s", core.pre_ticket_id, core.id)
            return
        if pre.status in _TICKET_FAIL:
            core.deal_status = MongoAutofixStatus.FAIL.value
            core.status_version = pre.status
            core.save(update_fields=update_fields)
        elif pre.status in _TICKET_RUNNING:
            if core.deal_status == MongoAutofixStatus.DETECTED.value:
                core.deal_status = MongoAutofixStatus.PRE_RUNNING.value
                core.save(update_fields=update_fields)
        elif pre.status in _TICKET_SUCCESS:
            # PRE 成功应已写入 ticket_id；若仍无则保持 ticketed 等待
            if core.deal_status == MongoAutofixStatus.PRE_RUNNING.value:
                core.deal_status = MongoAutofixStatus.TICKETED.value
                core.save(update_fields=update_fields)
        if core.deal_status != old_status:
            write_autofix_log(
                MongoAutofixLogEvent.STATUS,
                f"status {old_status} -> {core.deal_status} via pre={pre.id}({pre.status})",
                core=core,
                context={"ticket_status": pre.status, "old_status": old_status},
            )


@register_periodic_task(run_every=crontab(minute="*/2"))
def watch_mongod_backend_fault():
    """旁观者 member_state 发现 → 延迟/熔断/屏蔽 → 写 Core → 出 PRE."""
    try:
        created = discover_mongod_backend_faults()
        logger.info("watch_mongod_backend_fault created=%s", len(created))
    except Exception as exc:  # noqa: BLE001
        logger.exception("watch_mongod_backend_fault error: %s", exc)


@register_periodic_task(run_every=crontab(minute="*/2"))
def watch_mongod_autofix_flow():
    """盯 PRE / 修复替换单据状态，回写 MongoAutofixCore.deal_status."""
    cores = MongoAutofixCore.objects.filter(deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES)
    if not cores.exists():
        return
    for core in cores.iterator(chunk_size=100):
        try:
            _sync_core_from_tickets(core)
        except Exception as exc:  # noqa: BLE001
            logger.exception("watch_mongod_autofix_flow core=%s err=%s", core.id, exc)
            core.deal_status = MongoAutofixStatus.FAIL.value
            core.status_version = str(exc)[:64]
            core.save(update_fields=["deal_status", "status_version", "update_at"])
            write_autofix_log(MongoAutofixLogEvent.ERROR, f"sync status failed: {exc}", core=core)
