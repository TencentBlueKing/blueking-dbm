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
from backend.ticket.constants import TicketType

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


# ==================== SCENE_PRESERVED reports are never auto-repaired ====================


def test_periodic_repair_skips_scene_preserved_report():
    """SCENE_PRESERVED reports are never auto-repaired; the filter is only ROLLBACK_STARTED / ROLLBACK_SUCCEEDED."""
    report = _make_report(TaskStage.SCENE_PRESERVED, rollback_child_root_id="preserved_child")
    flow_tree = _make_flow_tree("preserved_child", StateType.FAILED)

    with _PATCH_EXERCISE_CFG, patch(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.task.wakeup_redis_rollback_runner_by_child",
        return_value=1,
    ) as mock_wakeup:
        _import_repair()()

    mock_wakeup.assert_not_called()
    report.delete()
    flow_tree.delete()
