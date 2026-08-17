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
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Hashable, List, Optional, Set, Tuple

from celery.schedules import crontab
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
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

RECYCLE_OLD_HOST = TicketType.RECYCLE_OLD_HOST
RECYCLE_APPLY_HOST = TicketType.RECYCLE_APPLY_HOST
RECYCLE_TICKET_TYPES = (RECYCLE_APPLY_HOST, RECYCLE_OLD_HOST)

TERMINAL_TICKET_STATUSES = (
    TicketStatus.SUCCEEDED,
    TicketStatus.FAILED,
    TicketStatus.TERMINATED,
    TicketStatus.REVOKED,
)
NON_TERMINAL_TICKET_STATUSES = (
    TicketStatus.PENDING,
    TicketStatus.APPROVE,
    TicketStatus.RESOURCE_REPLENISH,
    TicketStatus.TODO,
    TicketStatus.TIMER,
    TicketStatus.RUNNING,
)

# SUCCEEDED auto-hooks RECYCLE_OLD_HOST; terminate/fail paths expect RECYCLE_APPLY_HOST revoke cleanup.
EXPECTED_CLEANUP_CHILD_BY_STATUS = {
    TicketStatus.SUCCEEDED.value: RECYCLE_OLD_HOST,
    TicketStatus.FAILED.value: RECYCLE_APPLY_HOST,
    TicketStatus.TERMINATED.value: RECYCLE_APPLY_HOST,
    TicketStatus.REVOKED.value: RECYCLE_APPLY_HOST,
}

REASON_MISSING_CLEANUP = "missing_cleanup_child"
REASON_NON_TERMINAL_TIMEOUT = "non_terminal_timeout"
# SCENE_PRESERVED: wait for DBA skip+cleanup; do not flag as missing_cleanup
REASON_SCENE_PRESERVED = "scene_preserved"


@dataclass(frozen=True)
class TicketAnomaly:
    ticket_id: int
    bk_biz_id: int
    status: str
    reason: str
    detail: str
    update_at: datetime
    create_at: datetime
    url: str


def previous_two_calendar_days_range(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Return half-open ``[Day1 00:00, Day3 00:00)`` for a run on Day3.

    Example: at Day3 10:00 this includes Day1 00:00 through Day2 23:59:59.999999
    and excludes all Day3 tickets.
    """
    local_now = django_timezone.localtime(now or django_timezone.now())
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today_start - timedelta(days=2)
    return start, today_start


def _normalize_host_dict(host: dict) -> Optional[dict]:
    """Normalize a host dict to ``{bk_host_id, ip, bk_cloud_id, ...}``."""
    if not isinstance(host, dict):
        return None
    hid = host.get("bk_host_id") or host.get("host_id")
    ip = host.get("ip") or host.get("applied_ip")
    if hid is None and not ip:
        return None
    normalized = {
        "bk_host_id": hid,
        "ip": ip,
        "bk_cloud_id": host.get("bk_cloud_id", 0),
    }
    for key in ("os_type", "os_name", "device_class", "bk_biz_id", "remark"):
        if host.get(key) is not None:
            normalized[key] = host[key]
    return normalized


def _host_dedupe_key(host: dict) -> Optional[Hashable]:
    if host.get("bk_host_id") is not None:
        return host["bk_host_id"]
    return host.get("ip")


def _add_normalized_host(hosts_by_key: Dict, raw) -> None:
    h = _normalize_host_dict(raw if isinstance(raw, dict) else {})
    if not h:
        return
    key = _host_dedupe_key(h)
    if key is not None:
        hosts_by_key[key] = h


def extract_recycle_hosts(ticket: Ticket) -> List[dict]:
    """Extract applied hosts from drill ticket details (recycle_hosts / nodes / infos.redis)."""
    details = ticket.details or {}

    recycle_hosts = details.get("recycle_hosts") or []
    if recycle_hosts:
        hosts = [h for h in (_normalize_host_dict(x) for x in recycle_hosts) if h]
        if hosts:
            return hosts

    nodes = details.get("nodes") or {}
    if isinstance(nodes, dict) and nodes:
        hosts_by_key: Dict = {}
        for role_hosts in nodes.values():
            if not isinstance(role_hosts, list):
                continue
            for raw in role_hosts:
                if isinstance(raw, dict) and ("master" in raw or "slave" in raw):
                    for role in ("master", "slave"):
                        _add_normalized_host(hosts_by_key, raw.get(role) or {})
                    continue
                _add_normalized_host(hosts_by_key, raw)
        if hosts_by_key:
            return list(hosts_by_key.values())

    hosts_by_key = {}
    for info in details.get("infos") or []:
        for raw in info.get("redis") or []:
            _add_normalized_host(hosts_by_key, raw)
    return list(hosts_by_key.values())


def linked_recycle_ticket_types_by_parent(ticket_ids: List[int]) -> Dict[int, Set[str]]:
    """Return ``{parent_id: {recycle_ticket_type, ...}}`` via parent DELIVERY flows.

    ``Ticket.create_recycle_ticket`` registers a DELIVERY flow on the parent with
    ``details.related_ticket`` pointing to the recycle ticket. Query by indexed
    ``Flow.ticket_id`` instead of JSON ``details.parent_ticket`` on Ticket.
    """
    result: Dict[int, Set[str]] = {tid: set() for tid in ticket_ids}
    if not ticket_ids:
        return result

    related_by_parent: Dict[int, List[int]] = {}
    for flow in Flow.objects.filter(
        ticket_id__in=ticket_ids,
        flow_type=FlowType.DELIVERY.value,
    ).only("ticket_id", "details"):
        related_id = (flow.details or {}).get("related_ticket")
        if related_id:
            related_by_parent.setdefault(flow.ticket_id, []).append(related_id)

    all_related = {rid for ids in related_by_parent.values() for rid in ids}
    if not all_related:
        return result

    type_by_id = dict(
        Ticket.objects.filter(
            id__in=all_related,
            ticket_type__in=RECYCLE_TICKET_TYPES,
        ).values_list("id", "ticket_type")
    )
    for parent_id, related_ids in related_by_parent.items():
        for related_id in related_ids:
            ticket_type = type_by_id.get(related_id)
            if ticket_type:
                result.setdefault(parent_id, set()).add(ticket_type)
    return result


def ticket_has_recycle_ticket(ticket_id: int) -> bool:
    """Return True when the parent drill ticket already has any linked recycle ticket."""
    linked = linked_recycle_ticket_types_by_parent([ticket_id]).get(ticket_id) or set()
    return bool(linked)


def expected_cleanup_child_type(status: str) -> Optional[TicketType]:
    """Return the expected cleanup child ticket type for a terminal drill status."""
    return EXPECTED_CLEANUP_CHILD_BY_STATUS.get(getattr(status, "value", status))


def _format_elapsed(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes}m"
    if minutes:
        return f"{minutes}m{seconds}s"
    return f"{seconds}s"


def collect_redis_rollback_exercise_ticket_anomalies(
    polling_timeout: int, now: Optional[datetime] = None
) -> List[TicketAnomaly]:
    """Collect anomalous Redis rollback exercise tickets in the previous two calendar days."""
    now = now or django_timezone.now()
    window_start, window_end = previous_two_calendar_days_range(now)
    timeout_cutoff = now - timedelta(seconds=polling_timeout)

    tickets = list(
        Ticket.objects.filter(
            ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
            create_at__gte=window_start,
            create_at__lt=window_end,
        ).only("id", "bk_biz_id", "status", "details", "update_at", "create_at")
    )
    if not tickets:
        return []

    linked_types = linked_recycle_ticket_types_by_parent([t.id for t in tickets])
    # Batch-load preserved tickets so daily inspection does not flag missing_cleanup_child
    preserved_ticket_ids = set(
        Report.objects.filter(ticket_id__in=[t.id for t in tickets], task_stage=TaskStage.SCENE_PRESERVED).values_list(
            "ticket_id", flat=True
        )
    )
    anomalies: List[TicketAnomaly] = []

    for ticket in tickets:
        if ticket.id in preserved_ticket_ids:
            anomalies.append(
                TicketAnomaly(
                    ticket_id=ticket.id,
                    bk_biz_id=ticket.bk_biz_id,
                    status=ticket.status,
                    reason=REASON_SCENE_PRESERVED,
                    detail=_("现场保留待排查，需人工在页面跳过后清理"),
                    update_at=ticket.update_at,
                    create_at=ticket.create_at,
                    url=ticket.url,
                )
            )
            continue

        if ticket.status in NON_TERMINAL_TICKET_STATUSES:
            if ticket.update_at < timeout_cutoff:
                anomalies.append(
                    TicketAnomaly(
                        ticket_id=ticket.id,
                        bk_biz_id=ticket.bk_biz_id,
                        status=ticket.status,
                        reason=REASON_NON_TERMINAL_TIMEOUT,
                        detail=_("非终态超过 polling_timeout（{}s）未推进").format(polling_timeout),
                        update_at=ticket.update_at,
                        create_at=ticket.create_at,
                        url=ticket.url,
                    )
                )
            continue

        if ticket.status not in TERMINAL_TICKET_STATUSES:
            continue

        if not extract_recycle_hosts(ticket):
            continue

        expected = expected_cleanup_child_type(ticket.status)
        if expected is None:
            continue

        linked = linked_types.get(ticket.id) or set()
        if expected.value in linked:
            continue

        anomalies.append(
            TicketAnomaly(
                ticket_id=ticket.id,
                bk_biz_id=ticket.bk_biz_id,
                status=ticket.status,
                reason=REASON_MISSING_CLEANUP,
                detail=_("缺少关联清理单据 {}").format(expected),
                update_at=ticket.update_at,
                create_at=ticket.create_at,
                url=ticket.url,
            )
        )

    return anomalies


def _build_anomaly_rtx_content(bk_biz_id: int, anomalies: List[TicketAnomaly], now: datetime) -> str:
    lines = [
        _("业务ID: {}").format(bk_biz_id),
        _("异常单据数: {}").format(len(anomalies)),
        "",
    ]
    for idx, anomaly in enumerate(anomalies, start=1):
        elapsed = _format_elapsed(now - anomaly.update_at)
        lines.append(
            _("{idx}. 单据 {ticket_id} 状态={status} 原因={detail} " "距上次更新={elapsed} 创建于={create_at} {url}").format(
                idx=idx,
                ticket_id=anomaly.ticket_id,
                status=anomaly.status,
                detail=anomaly.detail,
                elapsed=elapsed,
                create_at=django_timezone.localtime(anomaly.create_at).strftime("%Y-%m-%d %H:%M:%S"),
                url=anomaly.url,
            )
        )
    return "\n".join(lines)


def notify_redis_rollback_exercise_ticket_anomalies(
    anomalies: List[TicketAnomaly], now: Optional[datetime] = None
) -> int:
    """Send one direct RTX summary to the drill biz's primary Redis DBA"""
    if not anomalies:
        return 0

    now = now or django_timezone.now()
    bk_biz_id = anomalies[0].bk_biz_id
    primary, _standby, _others = DBAdministrator.get_dba_for_db_type(bk_biz_id, DBType.Redis.value)
    if not primary:
        logger.warning(
            _("Skip Redis rollback exercise anomaly notify for biz {}: no Redis DBA configured").format(bk_biz_id)
        )
        return 0

    title = _("【DBM】Redis回档演练单据异常提醒")
    content = _build_anomaly_rtx_content(bk_biz_id, anomalies, now)
    try:
        CmsiHandler(title, content, list(primary)).send_rtx()
    except Exception:
        logger.exception(
            _("Failed to send Redis rollback exercise anomaly RTX for biz {} to {}").format(bk_biz_id, primary[0])
        )
        return 0

    logger.info(
        _("Notified Redis DBA {} for biz {} about {} rollback exercise ticket anomal(ies)").format(
            primary[0], bk_biz_id, len(anomalies)
        )
    )
    return 1


def detect_redis_rollback_exercise_ticket_anomalies(polling_timeout: int) -> int:
    """Detect anomalous drill tickets and notify the drill biz's primary Redis DBA."""
    now = django_timezone.now()
    anomalies = collect_redis_rollback_exercise_ticket_anomalies(polling_timeout, now=now)
    if not anomalies:
        logger.info(_("No Redis rollback exercise ticket anomalies found in previous two calendar days"))
        return 0

    logger.warning(_("Found {} Redis rollback exercise ticket anomal(ies)").format(len(anomalies)))
    return notify_redis_rollback_exercise_ticket_anomalies(anomalies, now=now)


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
    now = django_timezone.now()
    overdue_cutoff = now - timedelta(seconds=polling_timeout)
    long_overdue_cutoff = now - timedelta(seconds=polling_timeout * 3)

    # SCENE_PRESERVED is omitted on purpose: never auto-wakeup; DBA skip on the page.
    # Wakeup also guards FAILED runner nodes.
    reports = list(
        Report.objects.filter(
            task_stage__in=[TaskStage.ROLLBACK_STARTED, TaskStage.ROLLBACK_SUCCEEDED],
            update_at__lt=overdue_cutoff,
        ).only("id", "task_stage", "update_at", "delete_flow_obj_id", "rollback_flow_obj_id")
    )

    child_root_ids = []
    report_child_ids = []
    for report in reports:
        child_root_id = report.delete_flow_obj_id or report.rollback_flow_obj_id
        report_child_ids.append(child_root_id)
        if child_root_id:
            child_root_ids.append(child_root_id)

    flow_by_root = (
        FlowTree.objects.filter(root_id__in=child_root_ids).only("root_id", "status").in_bulk(field_name="root_id")
        if child_root_ids
        else {}
    )

    recovered = 0
    for report, child_root_id in zip(reports, report_child_ids):
        if not child_root_id:
            continue

        child_flow_tree = flow_by_root.get(child_root_id)
        if child_flow_tree is None:
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


@register_periodic_task(run_every=crontab(hour="10", minute="0"))
def redis_rollback_exercise_ticket_anomaly_detect():
    """
    Daily detector for Redis rollback exercise tickets missing cleanup or stuck non-terminal.
    """
    polling_timeout = RedisRollbackExercise().config.polling_timeout
    detect_redis_rollback_exercise_ticket_anomalies(polling_timeout)
