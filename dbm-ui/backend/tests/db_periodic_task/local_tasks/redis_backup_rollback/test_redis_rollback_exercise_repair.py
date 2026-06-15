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
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket

pytestmark = pytest.mark.django_db

_PATCH_EXERCISE_CFG = patch(
    "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.RedisRollbackExercise",
    return_value=SimpleNamespace(config=SimpleNamespace(polling_timeout=10)),
)


def _make_report(
    stage: str,
    rollback_child_root_id: str = "",
    delete_child_root_id: str = "",
    hours_ago: int = 2,
) -> Report:
    report = Report.objects.create(
        cluster_id=1,
        cluster_domain="d",
        cluster_type="Redis",
        instance_ip="127.0.0.1",
        instance_port=6379,
        redis_version="7.0",
        ticket_id=1,
        rollback_flow_obj_id=rollback_child_root_id,
        delete_flow_obj_id=delete_child_root_id,
        task_stage=stage,
    )
    Report.objects.filter(id=report.id).update(update_at=timezone.now() - timedelta(hours=hours_ago))
    report.refresh_from_db()
    return report


def _make_flow_tree(root_id: str, status: str):
    return FlowTree.objects.create(
        uid=1,
        bk_biz_id=1,
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
        root_id=root_id,
        tree={},
        status=status,
        created_by="tester",
    )


def _import_repair():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback.task import repair_stuck_redis_rollback_exercise

    return repair_stuck_redis_rollback_exercise


# ==================== Terminal child states trigger wakeup ====================


def test_periodic_repair_wakes_up_finished_child():
    report = _make_report(TaskStage.ROLLBACK_STARTED, rollback_child_root_id="child_root_id")
    flow_tree = _make_flow_tree("child_root_id", StateType.FINISHED)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_called_once_with(
        child_root_id="child_root_id", child_state=StateType.FINISHED, trigger="periodic_safety_net"
    )
    report.delete()
    flow_tree.delete()


@pytest.mark.parametrize("terminal_state", [StateType.FAILED, StateType.REVOKED])
def test_periodic_repair_wakes_up_failed_or_revoked_child(terminal_state):
    """FAILED and REVOKED children should also be woken up, not just FINISHED."""
    report = _make_report(TaskStage.ROLLBACK_STARTED, rollback_child_root_id="child_root_id")
    flow_tree = _make_flow_tree("child_root_id", terminal_state)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_called_once_with(
        child_root_id="child_root_id", child_state=terminal_state, trigger="periodic_safety_net"
    )
    report.delete()
    flow_tree.delete()


# ==================== ROLLBACK_SUCCEEDED stage is also picked up ====================


def test_periodic_repair_handles_rollback_succeeded_stage():
    """Reports in ROLLBACK_SUCCEEDED (waiting for cleanup child) should also be repaired."""
    report = _make_report(TaskStage.ROLLBACK_SUCCEEDED, rollback_child_root_id="child_root_id")
    flow_tree = _make_flow_tree("child_root_id", StateType.FINISHED)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_called_once()
    report.delete()
    flow_tree.delete()


# ==================== delete_flow_obj_id preferred over rollback_flow_obj_id ====================


def test_periodic_repair_prefers_delete_flow_obj_id():
    """When delete_flow_obj_id is set, it should be used (takes priority via `or`)."""
    report = _make_report(
        TaskStage.ROLLBACK_SUCCEEDED,
        rollback_child_root_id="rollback_root",
        delete_child_root_id="delete_root",
    )
    flow_tree = _make_flow_tree("delete_root", StateType.FINISHED)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_called_once_with(
        child_root_id="delete_root", child_state=StateType.FINISHED, trigger="periodic_safety_net"
    )
    report.delete()
    flow_tree.delete()


# ==================== Warning / skip paths ====================


def test_periodic_repair_warns_when_running_over_3_timeout():
    report = _make_report(TaskStage.ROLLBACK_STARTED, rollback_child_root_id="running_child_root_id")
    flow_tree = _make_flow_tree("running_child_root_id", StateType.RUNNING)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.logger.warning"
    ) as mock_warning:
        _import_repair()()

    assert mock_warning.called
    report.delete()
    flow_tree.delete()


def test_periodic_repair_skips_report_without_child_root_id():
    report = _make_report(TaskStage.ROLLBACK_STARTED)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child"
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_not_called()
    report.delete()


def test_periodic_repair_flowtree_not_found_under_3_timeout_silently_continues():
    """When FlowTree doesn't exist and report is not yet 3*timeout overdue, silently continue."""
    Report.objects.filter(task_stage__in=[TaskStage.ROLLBACK_STARTED, TaskStage.ROLLBACK_SUCCEEDED]).delete()
    report = _make_report(TaskStage.ROLLBACK_STARTED, rollback_child_root_id="missing_flow_child")

    with patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.RedisRollbackExercise",
        return_value=SimpleNamespace(config=SimpleNamespace(polling_timeout=3600)),
    ), patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child"
    ) as mock_wakeup, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.logger.warning"
    ) as mock_warning:
        _import_repair()()

    mock_wakeup.assert_not_called()
    mock_warning.assert_not_called()
    report.delete()


def test_periodic_repair_flowtree_not_found_over_3_timeout_warns():
    """When FlowTree doesn't exist and report exceeds 3*timeout, should emit warning."""
    report = _make_report(
        TaskStage.ROLLBACK_STARTED,
        rollback_child_root_id="missing_flow_child_old",
        hours_ago=24,
    )

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child"
    ) as mock_wakeup, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.logger.warning"
    ) as mock_warning:
        _import_repair()()

    mock_wakeup.assert_not_called()
    assert mock_warning.called
    report.delete()


# ==================== No overdue reports ====================


def test_periodic_repair_no_overdue_reports_is_noop():
    """When no reports match the overdue criteria, function should complete cleanly."""
    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child"
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_not_called()


# ==================== Multiple reports ====================


def test_periodic_repair_multiple_reports_accumulates_recovery():
    """When multiple reports have terminal children, recovered count should accumulate."""
    reports = []
    flow_trees = []
    for i in range(3):
        r = _make_report(TaskStage.ROLLBACK_STARTED, rollback_child_root_id=f"child_{i}")
        ft = _make_flow_tree(f"child_{i}", StateType.FINISHED)
        reports.append(r)
        flow_trees.append(ft)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.logger.info"
    ) as mock_info:
        _import_repair()()

    assert mock_wakeup.call_count == 3
    mock_info.assert_called()
    for r in reports:
        r.delete()
    for ft in flow_trees:
        ft.delete()


# ==================== Running child under 3*timeout is silently skipped ====================


def test_periodic_repair_running_child_under_3_timeout_no_warning():
    """A running child that hasn't exceeded 3*timeout should be silently skipped."""
    Report.objects.filter(task_stage__in=[TaskStage.ROLLBACK_STARTED, TaskStage.ROLLBACK_SUCCEEDED]).delete()
    report = _make_report(
        TaskStage.ROLLBACK_STARTED,
        rollback_child_root_id="running_child",
    )
    flow_tree = _make_flow_tree("running_child", StateType.RUNNING)

    with patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.RedisRollbackExercise",
        return_value=SimpleNamespace(config=SimpleNamespace(polling_timeout=3600)),
    ), patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child"
    ) as mock_wakeup, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.logger.warning"
    ) as mock_warning:
        _import_repair()()

    mock_wakeup.assert_not_called()
    mock_warning.assert_not_called()
    report.delete()
    flow_tree.delete()


# ==================== Missing recycle ticket repair ====================


def _make_drill_ticket(status: TicketStatus, details: dict, hours_ago: int = 2) -> Ticket:
    ticket = Ticket.objects.create(
        bk_biz_id=1,
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
        status=status,
        creator="tester",
        updater="tester",
        remark="drill ticket",
        details=details,
        group="redis",
    )
    Ticket.objects.filter(id=ticket.id).update(
        update_at=timezone.now() - timedelta(hours=hours_ago),
        create_at=timezone.now() - timedelta(days=1),
    )
    ticket.refresh_from_db()
    return ticket


def _import_recycle_repair():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback.task import (
        repair_missing_redis_rollback_recycle_tickets,
        resolve_missing_recycle_request,
        ticket_has_applied_hosts,
        ticket_has_recycle_ticket,
    )

    return (
        repair_missing_redis_rollback_recycle_tickets,
        resolve_missing_recycle_request,
        ticket_has_applied_hosts,
        ticket_has_recycle_ticket,
    )


def test_ticket_has_applied_hosts_from_recycle_hosts():
    ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [{"bk_host_id": 1, "ip": "1.1.1.1"}]})
    _, _, ticket_has_applied_hosts, _ = _import_recycle_repair()

    assert ticket_has_applied_hosts(ticket) is True
    ticket.delete()


def test_ticket_has_applied_hosts_from_infos_redis():
    ticket = _make_drill_ticket(
        TicketStatus.FAILED,
        {"infos": [{"redis": [{"bk_host_id": 2, "ip": "2.2.2.2", "bk_cloud_id": 0}]}]},
    )
    _, _, ticket_has_applied_hosts, _ = _import_recycle_repair()

    assert ticket_has_applied_hosts(ticket) is True
    ticket.delete()


def test_ticket_has_recycle_ticket_ignores_parent_ticket_without_delivery_flow():
    parent = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [{"bk_host_id": 1}]})
    recycle = Ticket.objects.create(
        bk_biz_id=1,
        ticket_type=TicketType.RECYCLE_OLD_HOST,
        status=TicketStatus.PENDING,
        creator="tester",
        updater="tester",
        remark="recycle",
        details={"parent_ticket": parent.id},
        group="common",
    )
    _, _, _, ticket_has_recycle_ticket = _import_recycle_repair()

    assert ticket_has_recycle_ticket(parent.id) is False
    recycle.delete()
    parent.delete()


def test_ticket_has_recycle_ticket_by_delivery_flow():
    parent = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [{"bk_host_id": 1}]})
    recycle = Ticket.objects.create(
        bk_biz_id=1,
        ticket_type=TicketType.RECYCLE_OLD_HOST,
        status=TicketStatus.PENDING,
        creator="tester",
        updater="tester",
        remark="recycle",
        details={"parent_ticket": parent.id},
        group="common",
    )
    Flow.objects.create(
        ticket=parent,
        flow_type=FlowType.DELIVERY.value,
        status=TicketFlowStatus.SUCCEEDED,
        details={"related_ticket": recycle.id},
        flow_alias="recycle",
    )
    _, _, _, ticket_has_recycle_ticket = _import_recycle_repair()

    assert ticket_has_recycle_ticket(parent.id) is True
    recycle.delete()
    parent.delete()


@pytest.mark.parametrize(
    ("status", "expected_type"),
    [
        (TicketStatus.SUCCEEDED, TicketType.RECYCLE_OLD_HOST),
        (TicketStatus.FAILED, TicketType.RECYCLE_OLD_HOST),
        (TicketStatus.TERMINATED, TicketType.RECYCLE_APPLY_HOST),
        (TicketStatus.REVOKED, TicketType.RECYCLE_OLD_HOST),
    ],
)
def test_resolve_missing_recycle_request(status, expected_type):
    ticket = _make_drill_ticket(
        status,
        {"recycle_hosts": [{"bk_host_id": 1, "ip": "1.1.1.1", "bk_cloud_id": 0}]},
    )
    _, resolve_missing_recycle_request, _, _ = _import_recycle_repair()

    recycle_type, recycle_hosts = resolve_missing_recycle_request(ticket)
    assert recycle_type == expected_type
    if expected_type == TicketType.RECYCLE_APPLY_HOST:
        assert recycle_hosts == []
    else:
        assert recycle_hosts == ticket.details["recycle_hosts"]
    ticket.delete()


def test_repair_missing_recycle_creates_ticket_for_terminal_drill():
    ticket = _make_drill_ticket(
        TicketStatus.FAILED,
        {"recycle_hosts": [{"bk_host_id": 1, "ip": "1.1.1.1", "bk_cloud_id": 0}]},
    )
    repair_missing_redis_rollback_recycle_tickets, _, _, _ = _import_recycle_repair()

    with patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.Ticket.create_recycle_ticket"
    ) as mock_create:
        repaired = repair_missing_redis_rollback_recycle_tickets(10)

    assert repaired == 1
    mock_create.assert_called_once_with(ticket.id, ticket.details["recycle_hosts"], TicketType.RECYCLE_OLD_HOST)
    ticket.delete()


def test_repair_missing_recycle_skips_when_recycle_exists():
    ticket = _make_drill_ticket(
        TicketStatus.SUCCEEDED,
        {"recycle_hosts": [{"bk_host_id": 1, "ip": "1.1.1.1", "bk_cloud_id": 0}]},
    )
    recycle = Ticket.objects.create(
        bk_biz_id=1,
        ticket_type=TicketType.RECYCLE_OLD_HOST,
        status=TicketStatus.PENDING,
        creator="tester",
        updater="tester",
        remark="recycle",
        details={"parent_ticket": ticket.id},
        group="common",
    )
    Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.DELIVERY.value,
        status=TicketFlowStatus.SUCCEEDED,
        details={"related_ticket": recycle.id},
        flow_alias="recycle",
    )
    repair_missing_redis_rollback_recycle_tickets, _, _, _ = _import_recycle_repair()

    with patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.Ticket.create_recycle_ticket"
    ) as mock_create:
        repaired = repair_missing_redis_rollback_recycle_tickets(10)

    assert repaired == 0
    mock_create.assert_not_called()
    recycle.delete()
    ticket.delete()


def test_repair_missing_recycle_skips_running_ticket():
    ticket = _make_drill_ticket(
        TicketStatus.RUNNING,
        {"recycle_hosts": [{"bk_host_id": 1, "ip": "1.1.1.1", "bk_cloud_id": 0}]},
    )
    repair_missing_redis_rollback_recycle_tickets, _, _, _ = _import_recycle_repair()

    with patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.Ticket.create_recycle_ticket"
    ) as mock_create:
        repaired = repair_missing_redis_rollback_recycle_tickets(10)

    assert repaired == 0
    mock_create.assert_not_called()
    ticket.delete()


def test_daily_recycle_repair_invokes_missing_recycle_repair():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback.task import (
        repair_missing_redis_rollback_exercise_recycle,
    )

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.repair_missing_redis_rollback_recycle_tickets"
    ) as mock_repair:
        repair_missing_redis_rollback_exercise_recycle()

    mock_repair.assert_called_once_with(10)
