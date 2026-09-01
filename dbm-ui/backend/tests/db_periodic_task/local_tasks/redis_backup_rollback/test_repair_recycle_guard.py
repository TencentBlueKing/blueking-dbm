# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Detector coverage for Redis rollback exercise ticket anomalies.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from backend.configuration.constants import DBType
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket

pytestmark = pytest.mark.django_db

TASK_MODULE = "backend.db_periodic_task.local_tasks.redis_backup_rollback.task"


def _import_mod():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback import task as mod

    return mod


def _host(ip="1.1.1.1", bk_host_id=101, bk_cloud_id=0):
    return {"ip": ip, "bk_host_id": bk_host_id, "bk_cloud_id": bk_cloud_id}


def _make_drill_ticket(
    status,
    details,
    *,
    bk_biz_id=1,
    create_offset_days=1,
    create_at=None,
    update_at=None,
):
    ticket = Ticket.objects.create(
        bk_biz_id=bk_biz_id,
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
        status=status,
        creator="tester",
        updater="tester",
        remark="drill ticket",
        details=details,
        group="redis",
    )
    now = timezone.now()
    local_now = timezone.localtime(now)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if create_at is None:
        create_at = today_start - timedelta(days=create_offset_days, hours=-12)
    if update_at is None:
        update_at = create_at
    Ticket.objects.filter(id=ticket.id).update(create_at=create_at, update_at=update_at)
    ticket.refresh_from_db()
    return ticket


def _link_recycle(parent: Ticket, recycle_type: TicketType):
    recycle = Ticket.objects.create(
        bk_biz_id=parent.bk_biz_id,
        ticket_type=recycle_type,
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
    return recycle


class TestCalendarWindow:
    def test_previous_two_calendar_days_range(self):
        mod = _import_mod()
        now = timezone.localtime(timezone.now()).replace(hour=10, minute=0, second=0, microsecond=0)
        start, end = mod.previous_two_calendar_days_range(now)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        assert start == today_start - timedelta(days=2)
        assert end == today_start

    def test_collect_includes_day1_midnight_excludes_day3(self):
        mod = _import_mod()
        now = timezone.localtime(timezone.now()).replace(hour=10, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day1_start = today_start - timedelta(days=2)

        included = _make_drill_ticket(
            TicketStatus.SUCCEEDED,
            {"recycle_hosts": [_host()]},
            create_at=day1_start,
            update_at=day1_start,
        )
        excluded = _make_drill_ticket(
            TicketStatus.SUCCEEDED,
            {"recycle_hosts": [_host(ip="2.2.2.2", bk_host_id=102)]},
            create_at=today_start,
            update_at=today_start,
        )

        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600, now=now)
        ids = {a.ticket_id for a in anomalies}
        assert included.id in ids
        assert excluded.id not in ids
        included.delete()
        excluded.delete()


class TestExpectedCleanupChild:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (TicketStatus.SUCCEEDED, TicketType.RECYCLE_OLD_HOST),
            (TicketStatus.FAILED, TicketType.RECYCLE_APPLY_HOST),
            (TicketStatus.TERMINATED, TicketType.RECYCLE_APPLY_HOST),
            (TicketStatus.REVOKED, TicketType.RECYCLE_APPLY_HOST),
        ],
    )
    def test_expected_cleanup_child_type(self, status, expected):
        mod = _import_mod()
        assert mod.expected_cleanup_child_type(status) == expected


class TestMissingCleanupDetection:
    def test_succeeded_missing_old_host_is_anomaly(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]})
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id and a.reason == mod.REASON_MISSING_CLEANUP for a in anomalies)
        ticket.delete()

    def test_terminated_missing_apply_host_is_anomaly(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.TERMINATED, {"recycle_hosts": [_host()]})
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id and a.reason == mod.REASON_MISSING_CLEANUP for a in anomalies)
        ticket.delete()

    def test_succeeded_with_old_host_link_is_clean(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]})
        recycle = _link_recycle(ticket, TicketType.RECYCLE_OLD_HOST)
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert all(a.ticket_id != ticket.id for a in anomalies)
        recycle.delete()
        ticket.delete()

    def test_wrong_cleanup_type_still_anomaly(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]})
        recycle = _link_recycle(ticket, TicketType.RECYCLE_APPLY_HOST)
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id and a.reason == mod.REASON_MISSING_CLEANUP for a in anomalies)
        recycle.delete()
        ticket.delete()

    def test_parent_ticket_json_alone_is_not_linkage(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]})
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
        assert mod.ticket_has_recycle_ticket(ticket.id) is False
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id for a in anomalies)
        recycle.delete()
        ticket.delete()

    def test_no_applied_hosts_skips_cleanup_check(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.FAILED, {"infos": []})
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert all(a.ticket_id != ticket.id for a in anomalies)
        ticket.delete()

    def test_extract_hosts_from_infos_redis(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(
            TicketStatus.FAILED,
            {"infos": [{"redis": [_host(ip="2.2.2.2", bk_host_id=102)]}]},
        )
        hosts = mod.extract_recycle_hosts(ticket)
        assert hosts
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id for a in anomalies)
        ticket.delete()


class TestNonTerminalTimeout:
    @pytest.mark.parametrize(
        "status",
        [
            TicketStatus.PENDING,
            TicketStatus.APPROVE,
            TicketStatus.RESOURCE_REPLENISH,
            TicketStatus.TODO,
            TicketStatus.TIMER,
            TicketStatus.RUNNING,
        ],
    )
    def test_non_terminal_past_timeout_is_anomaly(self, status):
        mod = _import_mod()
        now = timezone.now()
        ticket = _make_drill_ticket(
            status,
            {"recycle_hosts": [_host()]},
            update_at=now - timedelta(seconds=20),
        )
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(10, now=now)
        assert any(a.ticket_id == ticket.id and a.reason == mod.REASON_NON_TERMINAL_TIMEOUT for a in anomalies)
        ticket.delete()

    def test_non_terminal_within_timeout_is_clean(self):
        mod = _import_mod()
        now = timezone.now()
        ticket = _make_drill_ticket(
            TicketStatus.RUNNING,
            {"recycle_hosts": [_host()]},
            update_at=now - timedelta(seconds=5),
        )
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(10, now=now)
        assert all(a.ticket_id != ticket.id for a in anomalies)
        ticket.delete()


class TestNotifyGrouping:
    def test_one_rtx_to_first_anomaly_biz_primary_dba(self):
        mod = _import_mod()
        t1 = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]}, bk_biz_id=11)
        t2 = _make_drill_ticket(
            TicketStatus.FAILED,
            {"recycle_hosts": [_host(ip="2.2.2.2", bk_host_id=102)]},
            bk_biz_id=11,
        )
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)

        def fake_dba(bk_biz_id, db_type):
            assert bk_biz_id == 11
            assert db_type == DBType.Redis.value
            return (["dba-11"], [], [])

        with patch(f"{TASK_MODULE}.DBAdministrator.get_dba_for_db_type", side_effect=fake_dba) as mock_dba, patch(
            f"{TASK_MODULE}.CmsiHandler"
        ) as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler_cls.return_value = mock_handler
            notified = mod.notify_redis_rollback_exercise_ticket_anomalies(anomalies)

        assert notified == 1
        mock_dba.assert_called_once_with(11, DBType.Redis.value)
        mock_handler_cls.assert_called_once()
        assert mock_handler_cls.call_args.args[2] == ["dba-11"]
        content = mock_handler_cls.call_args.args[1]
        assert str(t1.id) in content
        assert str(t2.id) in content
        mock_handler.send_rtx.assert_called_once()
        t1.delete()
        t2.delete()

    def test_no_notify_when_clean(self):
        mod = _import_mod()
        with patch(f"{TASK_MODULE}.CmsiHandler") as mock_handler_cls:
            notified = mod.notify_redis_rollback_exercise_ticket_anomalies([])
        assert notified == 0
        mock_handler_cls.assert_not_called()

    def test_detect_never_creates_recycle_or_loads_residue(self):
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.SUCCEEDED, {"recycle_hosts": [_host()]})

        with patch(f"{TASK_MODULE}.Ticket.create_recycle_ticket") as mock_create, patch(
            f"{TASK_MODULE}.DBAdministrator.get_dba_for_db_type", return_value=(["dba-1"], [], [])
        ), patch(f"{TASK_MODULE}.CmsiHandler") as mock_handler_cls:
            mock_handler_cls.return_value = MagicMock()
            # Residue helpers were removed; attribute must not exist on the module.
            assert not hasattr(mod, "load_meta_residue")
            assert not hasattr(mod, "filter_hosts_for_recycle")
            mod.detect_redis_rollback_exercise_ticket_anomalies(3600)

        mock_create.assert_not_called()
        ticket.delete()


class TestPeriodicRegistration:
    def test_daily_detector_invokes_detect(self):
        mod = _import_mod()
        with patch(
            f"{TASK_MODULE}.RedisRollbackExercise",
            return_value=SimpleNamespace(config=SimpleNamespace(polling_timeout=10)),
        ), patch(f"{TASK_MODULE}.detect_redis_rollback_exercise_ticket_anomalies") as mock_detect:
            mod.redis_rollback_exercise_ticket_anomaly_detect()
        mock_detect.assert_called_once_with(10)

    def test_detector_is_exported_and_callable(self):
        mod = _import_mod()
        assert callable(mod.redis_rollback_exercise_ticket_anomaly_detect)
        from backend.db_periodic_task.local_tasks.redis_backup_rollback import (
            redis_rollback_exercise_ticket_anomaly_detect,
        )

        assert redis_rollback_exercise_ticket_anomaly_detect is mod.redis_rollback_exercise_ticket_anomaly_detect


class TestScenePreservedDetection:
    def test_preserved_ticket_reports_scene_preserved_reason(self):
        """Preserved tickets report REASON_SCENE_PRESERVED, not a daily missing_cleanup_child false positive."""
        from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
        from backend.db_report.models import RedisRollbackExerciseReport as Report

        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.FAILED, {"recycle_hosts": [_host()]})
        report = Report.objects.create(
            cluster_id=1,
            cluster_domain="d",
            cluster_type="Redis",
            instance_ip="127.0.0.1",
            instance_port=6379,
            redis_version="7.0",
            ticket_id=ticket.id,
            task_stage=TaskStage.SCENE_PRESERVED,
        )
        try:
            anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
            preserved = [a for a in anomalies if a.ticket_id == ticket.id]
            assert len(preserved) == 1
            assert preserved[0].reason == mod.REASON_SCENE_PRESERVED
            assert not any(a.ticket_id == ticket.id and a.reason == mod.REASON_MISSING_CLEANUP for a in anomalies)
        finally:
            report.delete()
            ticket.delete()

    def test_failed_ticket_without_preserved_report_stays_missing_cleanup(self):
        """Control: a FAILED ticket without a preserved report still flags missing_cleanup."""
        mod = _import_mod()
        ticket = _make_drill_ticket(TicketStatus.FAILED, {"recycle_hosts": [_host()]})
        anomalies = mod.collect_redis_rollback_exercise_ticket_anomalies(3600)
        assert any(a.ticket_id == ticket.id and a.reason == mod.REASON_MISSING_CLEANUP for a in anomalies)
        ticket.delete()
