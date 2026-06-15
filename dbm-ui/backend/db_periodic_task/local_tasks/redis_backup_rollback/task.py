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

from celery.schedules import crontab
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.flow.signal.redis_rollback_exercise_handler import wakeup_redis_rollback_runner_by_child
from backend.ticket.constants import FlowType, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket

from .base import RedisRollbackExercise

logger = logging.getLogger("root")

RECYCLE_TICKET_TYPES = (TicketType.RECYCLE_APPLY_HOST, TicketType.RECYCLE_OLD_HOST)
TERMINAL_TICKET_STATUSES = (
    TicketStatus.SUCCEEDED,
    TicketStatus.FAILED,
    TicketStatus.TERMINATED,
    TicketStatus.REVOKED,
)
RECENT_TICKET_LOOKBACK_DAYS = 2


def ticket_has_applied_hosts(ticket: Ticket) -> bool:
    """Return True when rollback exercise ticket details contain applied resource hosts."""
    recycle_hosts = ticket.details.get("recycle_hosts") or []
    if recycle_hosts:
        return True

    for info in ticket.details.get("infos") or []:
        if info.get("redis"):
            return True
    return False


def ticket_has_recycle_ticket(ticket_id: int) -> bool:
    """Return True when the parent drill ticket already has a linked recycle ticket.

    ``Ticket.create_recycle_ticket`` registers a DELIVERY flow on the parent with
    ``details.related_ticket`` pointing to the recycle ticket. Query by indexed
    ``Flow.ticket_id`` instead of JSON ``details.parent_ticket`` on Ticket.
    """
    related_ticket_ids = []
    for flow in Flow.objects.filter(
        ticket_id=ticket_id,
        flow_type=FlowType.DELIVERY.value,
    ).only("details"):
        related_id = (flow.details or {}).get("related_ticket")
        if related_id:
            related_ticket_ids.append(related_id)

    if not related_ticket_ids:
        return False

    return Ticket.objects.filter(
        id__in=related_ticket_ids,
        ticket_type__in=RECYCLE_TICKET_TYPES,
    ).exists()


def resolve_missing_recycle_request(ticket: Ticket) -> tuple[TicketType, list]:
    """Choose recycle ticket type/hosts for a drill ticket missing recycle linkage."""
    recycle_hosts = ticket.details.get("recycle_hosts") or []
    if ticket.status == TicketStatus.TERMINATED:
        return TicketType.RECYCLE_APPLY_HOST, []
    return TicketType.RECYCLE_OLD_HOST, recycle_hosts


def repair_missing_redis_rollback_recycle_tickets(polling_timeout: int) -> int:
    """
    Best-effort safety net for drill tickets that applied hosts but missed recycle creation.
    """
    now = django_timezone.now()
    grace_cutoff = now - timedelta(seconds=polling_timeout)
    recent_cutoff = now - timedelta(days=RECENT_TICKET_LOOKBACK_DAYS)

    tickets = Ticket.objects.filter(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
        status__in=TERMINAL_TICKET_STATUSES,
        update_at__lt=grace_cutoff,
        create_at__gte=recent_cutoff,
    ).only("id", "status", "details")

    repaired = 0
    for ticket in tickets:
        if not ticket_has_applied_hosts(ticket):
            continue
        if ticket_has_recycle_ticket(ticket.id):
            continue

        recycle_type, recycle_hosts = resolve_missing_recycle_request(ticket)
        logger.warning(
            _("Redis rollback exercise ticket {} is {} with applied hosts but no recycle ticket; creating {}").format(
                ticket.id, ticket.status, recycle_type
            )
        )
        Ticket.create_recycle_ticket(ticket.id, recycle_hosts, recycle_type)
        repaired += 1

    if repaired:
        logger.info(_("Created {} missing redis rollback recycle ticket(s)").format(repaired))
    return repaired


@register_periodic_task(run_every=crontab(day_of_week="0", hour="12", minute="0"))
def init_redis_rollback_candidates():
    """
    Init candidates to exericise each week
    """
    RedisRollbackExercise().init_candidates_queue()


@register_periodic_task(run_every=crontab(day_of_week="1-5", hour="9-17", minute="*/10"))
def redis_rollback_exercise():
    """
    Generate Redis rollback exercise tasks
    """
    RedisRollbackExercise().start()


@register_periodic_task(run_every=crontab(minute="0"))
def repair_stuck_redis_rollback_exercise():
    """
    Best-effort safety net for stuck rollback exercise reports.
    """
    exercise_cfg = RedisRollbackExercise().config
    polling_timeout = exercise_cfg.polling_timeout
    overdue_cutoff = django_timezone.now() - timedelta(seconds=polling_timeout)
    long_overdue_cutoff = django_timezone.now() - timedelta(seconds=polling_timeout * 3)

    reports = Report.objects.filter(
        task_stage__in=[TaskStage.ROLLBACK_STARTED, TaskStage.ROLLBACK_SUCCEEDED], update_at__lt=overdue_cutoff
    )

    recovered = 0
    for report in reports:
        child_root_id = report.delete_flow_obj_id or report.rollback_flow_obj_id
        if not child_root_id:
            continue

        try:
            child_flow_tree = FlowTree.objects.get(root_id=child_root_id)
        except FlowTree.DoesNotExist:
            if report.update_at < long_overdue_cutoff:
                logger.warning(
                    _("Redis rollback report {} has no child FlowTree and exceeds 3*timeout").format(report.id)
                )
            continue

        if child_flow_tree.status in [StateType.FINISHED, StateType.FAILED, StateType.REVOKED]:
            recovered += wakeup_redis_rollback_runner_by_child(
                child_root_id=child_root_id, child_state=child_flow_tree.status, trigger="periodic_safety_net"
            )
        elif report.update_at < long_overdue_cutoff:
            logger.warning(
                _("Redis rollback report {} still in stage {} with child flow {} state {} (>3*timeout)").format(
                    report.id, report.task_stage, child_root_id, child_flow_tree.status
                )
            )

    if recovered:
        logger.info(_("Recovered {} stuck redis rollback runner(s)").format(recovered))


@register_periodic_task(run_every=crontab(hour="3", minute="0"))
def repair_missing_redis_rollback_exercise_recycle():
    """
    Daily safety net for drill tickets that applied hosts but missed recycle creation.
    """
    polling_timeout = RedisRollbackExercise().config.polling_timeout
    repair_missing_redis_rollback_recycle_tickets(polling_timeout)
