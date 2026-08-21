# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Unit tests for the Redis rollback exercise trigger logic.

Covers:
- Pure helpers: _resolve_tendis_type, _cluster_type_has_binlog, _summarize_binlog,
  RedisRollbackExerciseConfig defaults.
- Report.mark() state mapping including the BACKUP_INVALID -> ABNORMAL transition.
- _instance_has_backup paths (cache, SSD happy/gap, Tendisplus kvstorecount, day iteration).
- _validate_instance failure-kind dispatch.
- SPECIFIED mode (_get_specified_instances / _pick_target_instances) dispatch,
  biz allowlist filtering, and biz-only discovery.
- Weighted random selection strategy: multiplicative weight multipliers and the
  A-Res (Efraimidis-Spirakis) sampling algorithm.

Source-module imports are done lazily through _base()/_exercise_cls()/etc. to avoid
triggering ``backend.db_periodic_task.local_tasks/__init__.py`` at collection time
(which calls ``register_periodic_task`` -> DB writes before pytest-django enables DB
access). Same convention as the sibling ``test_redis_rollback_exercise_repair.py``.
"""
import random
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_report.enums import REDIS_ROLLBACK_EXER_FAILED_STAGES
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.enums import ReportStateType
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.exceptions import AppBaseException
from backend.utils.time import datetime2str, str2datetime

pytestmark = pytest.mark.django_db

# String path used by `patch(...)` decorators below — `patch` resolves lazily.
BASE_MODULE = "backend.db_periodic_task.local_tasks.redis_backup_rollback.base"
CONFIG_MODULE = "backend.db_services.redis.rollback.config"

# Aware ISO timestamps so str2datetime's aware_check passes.
FULL_BK_UPTIME = "2026-04-15T05:01:23+08:00"
FULL_BK_FILE_MTIME = "2026-04-15T05:00:11+08:00"


# ---------------------------------------------------------------------------
# Lazy import shims (see module docstring for why).
# ---------------------------------------------------------------------------


def _base():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback import base as _b

    return _b


def _exercise_cls():
    return _base().RedisRollbackExercise


def _config_cls():
    return _base().RedisRollbackExerciseConfig


def _failure_kind():
    return _base().ValidationFailureKind


def _mode_enum():
    return _base().RedisRollbackExerciseMode


def _make_exercise(**config_overrides):
    """Build a RedisRollbackExercise without touching SystemSettings.

    Optional kwargs are forwarded to RedisRollbackExerciseConfig so individual
    tests can override fields (e.g. mode, specified_domains, weight multipliers).
    """
    cls = _exercise_cls()
    cfg = _config_cls()(**config_overrides)
    with patch.object(cls, "_init_config", return_value=cfg):
        return cls()


# ---------------------------------------------------------------------------
# Local helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cluster_mock(cluster_type: str, id_: int = 1):
    """Return a MagicMock with the attributes _instance_has_backup / _get_kvstorecount read."""
    cluster = MagicMock(name=f"Cluster<{cluster_type}>")
    cluster.id = id_
    cluster.cluster_type = cluster_type
    cluster.bk_biz_id = 100
    cluster.bk_cloud_id = 0
    cluster.immute_domain = f"test-{cluster_type.lower()}.dba.db"
    cluster.major_version = "Redis-6"
    return cluster


def _fake_cluster(cluster_id: int, bk_biz_id: int, immute_domain: str, bk_cloud_id: int = 0) -> MagicMock:
    """Lightweight cluster mock for SPECIFIED-mode tests (only id/biz/domain matter)."""
    cluster = MagicMock(name=f"Cluster<{immute_domain}>")
    cluster.id = cluster_id
    cluster.bk_biz_id = bk_biz_id
    cluster.bk_cloud_id = bk_cloud_id
    cluster.immute_domain = immute_domain
    return cluster


def _fake_selection(cluster: MagicMock) -> dict:
    return {
        "cluster": cluster,
        "instance": SimpleNamespace(ip_port="m:1"),
        "backup_check_instance": SimpleNamespace(ip_port="s:1"),
    }


def _make_full_backup_log(
    uptime_iso: str = FULL_BK_UPTIME,
    file_last_mtime_iso: str = FULL_BK_FILE_MTIME,
    status: str = "to_backup_system_success",
) -> dict:
    """Mirror the dict shape produced by DataStructureHandler.query_latest_backup_log."""
    return {
        "file_tag": "REDIS_FULL",
        "status": status,
        "uptime": uptime_iso,
        "file_last_mtime": file_last_mtime_iso,
        "size": 178635,
        "source_ip": "3.3.3.3",
        "task_id": "tid-1",
        "file_name": "redis-slave-1-30000-20260415050011.aof.zst",
        "shard_value": "0-5461",
    }


def _make_binlog_file(name: str, size: int, mtime: str) -> dict:
    """Mirror one entry returned by DataStructureHandler.query_binlog_from_bklog."""
    return {
        "file_tag": "REDIS_BINLOG",
        "status": "to_backup_system_success",
        "uptime": mtime,
        "file_last_mtime": mtime,
        "size": size,
        "source_ip": "3.3.3.3",
        "server_port": 30000,
        "task_id": f"tid-{name}",
        "file_name": name,
        "shard_value": "0-5461",
    }


# ---------------------------------------------------------------------------
# 1) Pure helpers (no DB, no mocks)
# ---------------------------------------------------------------------------


class TestPureHelpers:
    """Helpers that should be safe to test without any DB / mocking."""

    def test_resolve_tendis_type_redis_family(self):
        resolve = _exercise_cls()._resolve_tendis_type
        for ct in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TendisRedisInstance.value,
            ClusterType.TendisPredixyRedisCluster.value,
        ]:
            assert resolve(ct) == ClusterType.RedisInstance.value

    def test_resolve_tendis_type_ssd(self):
        resolve = _exercise_cls()._resolve_tendis_type
        assert resolve(ClusterType.TwemproxyTendisSSDInstance.value) == ClusterType.TendisSSDInstance.value

    def test_resolve_tendis_type_tendisplus(self):
        resolve = _exercise_cls()._resolve_tendis_type
        assert resolve(ClusterType.TendisPredixyTendisplusCluster.value) == ClusterType.TendisplusInstance.value

    def test_resolve_tendis_type_unknown_raises(self):
        with pytest.raises(NotImplementedError):
            _exercise_cls()._resolve_tendis_type("not_a_real_cluster_type")

    def test_cluster_type_has_binlog_true(self):
        has_binlog = _exercise_cls()._cluster_type_has_binlog
        assert has_binlog(ClusterType.TwemproxyTendisSSDInstance.value) is True
        assert has_binlog(ClusterType.TendisPredixyTendisplusCluster.value) is True

    def test_cluster_type_has_binlog_false(self):
        has_binlog = _exercise_cls()._cluster_type_has_binlog
        for ct in [
            ClusterType.TendisTwemproxyRedisInstance.value,  # cache
            ClusterType.TendisRedisInstance.value,  # main-slave
            ClusterType.TendisPredixyRedisCluster.value,  # predixy redis cluster
        ]:
            assert has_binlog(ct) is False

    def test_summarize_binlog_empty(self):
        assert _exercise_cls()._summarize_binlog([]) == {"count": 0, "total_size_bytes": 0}

    def test_summarize_binlog_single(self):
        binlogs = [_make_binlog_file("binlog-a.log.zst", 1024, "2026-04-15T05:30:00+08:00")]

        summary = _exercise_cls()._summarize_binlog(binlogs)

        assert summary["count"] == 1
        assert summary["total_size_bytes"] == 1024
        assert summary["earliest_start_time"] == summary["latest_start_time"] == "2026-04-15T05:30:00+08:00"
        assert summary["first_file"] == summary["last_file"] == "binlog-a.log.zst"

    def test_summarize_binlog_multiple(self):
        binlogs = [
            _make_binlog_file("binlog-a.log.zst", 100, "2026-04-15T05:30:00+08:00"),
            _make_binlog_file("binlog-b.log.zst", 200, "2026-04-15T06:30:00+08:00"),
            _make_binlog_file("binlog-c.log.zst", 300, "2026-04-16T04:48:00+08:00"),
        ]

        summary = _exercise_cls()._summarize_binlog(binlogs)

        assert summary["count"] == 3
        assert summary["total_size_bytes"] == 600
        assert summary["earliest_start_time"] == "2026-04-15T05:30:00+08:00"
        assert summary["latest_start_time"] == "2026-04-16T04:48:00+08:00"
        # first_file / last_file follow input order, NOT time order
        assert summary["first_file"] == "binlog-a.log.zst"
        assert summary["last_file"] == "binlog-c.log.zst"

    def test_config_default_offsets(self):
        """Regression guard for the new replay-window knobs."""
        cfg = _config_cls()()
        assert cfg.binlog_replay_minutes == 1430
        assert cfg.no_binlog_offset_minutes == 30
        assert cfg.bk_cloud_ids is None
        assert cfg.ai_analysis_enabled is False

    def test_config_preserve_scene_defaults(self):
        """Preserve-mode defaults: stop and keep the scene; 72h alarm shield."""
        cfg = _config_cls()()
        assert cfg.error_ignorable is False
        assert cfg.preserve_scene_shield_minutes == 4320

    def test_config_from_settings_ignores_unknown_keys(self):
        """shell_plus-friendly loader should tolerate stale keys in SystemSettings."""
        with patch(
            f"{CONFIG_MODULE}.SystemSettings.get_setting_value",
            return_value={"enabled": True, "max_instances": 3, "bk_cloud_ids": [0, 2000000], "stale_key": "ignored"},
        ) as mock_get:
            cfg = _config_cls().from_settings()

        assert cfg.enabled is True
        assert cfg.max_instances == 3
        assert cfg.bk_cloud_ids == [0, 2000000]
        assert not hasattr(cfg, "stale_key")
        mock_get.assert_called_once()

    def test_config_from_settings_non_dict_uses_defaults(self):
        with patch(f"{CONFIG_MODULE}.SystemSettings.get_setting_value", return_value="bad"):
            cfg = _config_cls().from_settings()

        assert cfg == _config_cls()()

    def test_config_save_to_settings(self):
        cfg = _config_cls()(enabled=True, max_instances=7)

        with patch(f"{CONFIG_MODULE}.SystemSettings.insert_setting_value") as mock_insert:
            cfg.save_to_settings(user="tester")

        mock_insert.assert_called_once()
        call_kwargs = mock_insert.call_args.kwargs
        assert call_kwargs["key"] == "REDIS_ROLLBACK_EXERCISE"
        assert call_kwargs["value_type"] == "dict"
        assert call_kwargs["user"] == "tester"
        assert call_kwargs["value"]["enabled"] is True
        assert call_kwargs["value"]["max_instances"] == 7


# ---------------------------------------------------------------------------
# 2) Report.mark() state mapping (DB)
# ---------------------------------------------------------------------------


class TestReportStateMapping(TestCase):
    """Verify Report.mark() maps task stages to the right ReportStateType."""

    # RedisRollbackExerciseReport lives in the ``report_db`` database (separate from
    # ``default``); Django TestCase requires every non-default DB used by the test
    # body to be listed here so it gets wrapped in a transaction and isolated.
    databases = {"default", "report_db"}

    def setUp(self):
        self.common_kwargs = dict(
            bk_biz_id=100,
            bk_cloud_id=0,
            cluster_id=10001,
            cluster_domain="test-cluster.dba.db",
            cluster_type=ClusterType.TwemproxyTendisSSDInstance.value,
            instance_ip="3.3.3.3",
            instance_port=30000,
            redis_version="6.2.7",
            task_stage=TaskStage.TASK_GENERATED,
            creator="system",
            updater="system",
        )

    def tearDown(self):
        Report.objects.all().delete()

    def test_mark_backup_invalid_maps_to_abnormal(self):
        report = Report.objects.create(**self.common_kwargs)

        report.mark(TaskStage.BACKUP_INVALID, task_message="binlog gap")
        report.refresh_from_db()

        assert report.task_stage == TaskStage.BACKUP_INVALID
        assert report.state == ReportStateType.ABNORMAL
        assert report.task_end_time is not None
        assert report.task_message == "binlog gap"

    def test_mark_skipped_still_maps_to_warning(self):
        report = Report.objects.create(**self.common_kwargs)

        report.mark(TaskStage.SKIPPED, task_message="cluster offline")
        report.refresh_from_db()

        assert report.task_stage == TaskStage.SKIPPED
        assert report.state == ReportStateType.WARNING
        assert report.task_end_time is not None

    def test_mark_done_maps_to_normal(self):
        report = Report.objects.create(**self.common_kwargs)

        report.mark(TaskStage.DONE)
        report.refresh_from_db()

        assert report.task_stage == TaskStage.DONE
        assert report.state == ReportStateType.NORMAL
        assert report.task_end_time is not None

    def test_backup_invalid_in_failed_stages(self):
        assert TaskStage.BACKUP_INVALID in REDIS_ROLLBACK_EXER_FAILED_STAGES

    def test_scene_preserved_in_failed_stages(self):
        assert TaskStage.SCENE_PRESERVED in REDIS_ROLLBACK_EXER_FAILED_STAGES

    def test_mark_scene_preserved_then_rollback_failed_transition(self):
        """SCENE_PRESERVED stays open until DBA confirmation marks a terminal failure."""
        report = Report.objects.create(**self.common_kwargs)

        report.mark(TaskStage.SCENE_PRESERVED, task_message="scene held")
        report.refresh_from_db()

        assert report.task_stage == TaskStage.SCENE_PRESERVED
        assert report.state == ReportStateType.ABNORMAL
        assert report.recover_end_time is not None
        assert report.task_end_time is None

        # Drill ends as failed: SCENE_PRESERVED -> ROLLBACK_FAILED overwrites the stage and fills task_end_time
        report.mark(TaskStage.ROLLBACK_FAILED, task_message="rollback failed")
        report.refresh_from_db()

        assert report.task_stage == TaskStage.ROLLBACK_FAILED
        assert report.state == ReportStateType.ABNORMAL
        assert report.task_end_time is not None

    def test_get_previously_failed_clusters_picks_backup_invalid(self):
        kwargs = dict(self.common_kwargs)
        kwargs["cluster_id"] = 20002
        report = Report.objects.create(**kwargs)
        report.mark(TaskStage.BACKUP_INVALID, task_message="missing full backup")

        failed_set, _ = Report.get_previously_failed_clusters()

        assert 20002 in failed_set


# ---------------------------------------------------------------------------
# 3) _instance_has_backup behavior (mocked DataStructureHandler / DBConfigApi)
# ---------------------------------------------------------------------------


class TestInstanceHasBackup:
    """Drive _instance_has_backup with a mocked DataStructureHandler."""

    def test_cache_cluster_skips_binlog_query_and_uses_30min_offset(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TendisTwemproxyRedisInstance.value)

        handler = MagicMock()
        handler.query_latest_backup_log.return_value = _make_full_backup_log()
        handler.query_binlog_from_bklog = MagicMock(side_effect=AssertionError("must not be called for cache"))

        with patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler):
            has_backup, full_backup, days_used, rtp, binlog_summary, fail_reason = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert has_backup is True
        assert full_backup is not None
        assert days_used == 1
        assert binlog_summary is None
        assert fail_reason is None
        # Cache uses no_binlog_offset_minutes (30) past uptime
        expected = str2datetime(FULL_BK_UPTIME) + timedelta(minutes=30)
        assert rtp == expected
        handler.query_latest_backup_log.assert_called_once()
        handler.query_binlog_from_bklog.assert_not_called()

    def test_ssd_happy_path_uses_replay_minutes_and_summarizes_binlog(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)
        binlogs = [
            _make_binlog_file("binlog-a.log.zst", 100, "2026-04-15T05:30:00+08:00"),
            _make_binlog_file("binlog-b.log.zst", 200, "2026-04-16T01:00:00+08:00"),
            _make_binlog_file("binlog-c.log.zst", 300, "2026-04-16T04:40:00+08:00"),
        ]

        handler = MagicMock()
        handler.query_latest_backup_log.return_value = _make_full_backup_log()
        handler.query_binlog_from_bklog.return_value = binlogs

        with patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler):
            has_backup, full_backup, days_used, rtp, binlog_summary, fail_reason = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert has_backup is True
        assert fail_reason is None
        assert days_used == 1
        assert binlog_summary["count"] == 3
        assert binlog_summary["total_size_bytes"] == 600
        # SSD uses binlog_replay_minutes (1430) past uptime
        expected_rtp = str2datetime(FULL_BK_UPTIME) + timedelta(minutes=1430)
        assert rtp == expected_rtp

        # query_binlog_from_bklog was invoked with the full-backup mtime as start and rtp as end
        call_kwargs = handler.query_binlog_from_bklog.call_args.kwargs
        assert call_kwargs["start_time"] == str2datetime(FULL_BK_FILE_MTIME)
        assert call_kwargs["end_time"] == expected_rtp
        assert call_kwargs["host_ip"] == "3.3.3.3"
        assert call_kwargs["port"] == 30000
        assert call_kwargs["tendis_type"] == ClusterType.TendisSSDInstance.value
        assert call_kwargs["kvstorecount"] is None

    def test_ssd_binlog_gap_raises_appbaseexception_and_loop_exhausts(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)

        handler = MagicMock()
        handler.query_latest_backup_log.return_value = _make_full_backup_log()
        handler.query_binlog_from_bklog.side_effect = AppBaseException("missing binlog index 42")

        with patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler):
            has_backup, full_backup, days_used, rtp, binlog_summary, fail_reason = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1, 2],
            )

        assert has_backup is False
        assert full_backup is None
        assert days_used is None
        assert rtp is None
        assert binlog_summary is None
        assert fail_reason is not None
        assert "Binlog invalid" in fail_reason
        # Tried both rollback_days entries
        assert handler.query_latest_backup_log.call_count == 2
        assert handler.query_binlog_from_bklog.call_count == 2

    def test_full_backup_missing_across_all_days(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TendisTwemproxyRedisInstance.value)

        handler = MagicMock()
        handler.query_latest_backup_log.return_value = None  # nothing returned for any day

        with patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler):
            has_backup, full_backup, days_used, rtp, binlog_summary, fail_reason = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1, 3, 7],
            )

        assert has_backup is False
        assert full_backup is None
        assert days_used is None
        assert rtp is None
        assert binlog_summary is None
        assert fail_reason is not None
        assert handler.query_latest_backup_log.call_count == 3

    def test_day_iteration_sorts_and_returns_first_success(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TendisTwemproxyRedisInstance.value)

        # rollback_days passed as [7, 3, 1] -> sorted to [1, 3, 7].
        # Day 1 returns missing, day 3 returns success.
        handler = MagicMock()
        handler.query_latest_backup_log.side_effect = [None, _make_full_backup_log()]

        with patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler):
            has_backup, _, days_used, _, _, _ = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[7, 3, 1],
            )

        assert has_backup is True
        assert days_used == 3
        assert handler.query_latest_backup_log.call_count == 2

    def test_tendisplus_passes_kvstorecount_and_correct_tendis_type(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TendisPredixyTendisplusCluster.value)

        handler = MagicMock()
        handler.query_latest_backup_log.return_value = _make_full_backup_log()
        handler.query_binlog_from_bklog.return_value = [
            _make_binlog_file("binlog-tplus-a.log.zst", 100, "2026-04-15T06:00:00+08:00"),
            _make_binlog_file("binlog-tplus-b.log.zst", 200, "2026-04-16T03:00:00+08:00"),
        ]

        with (
            patch(f"{BASE_MODULE}.DataStructureHandler", return_value=handler),
            patch(
                f"{BASE_MODULE}.DBConfigApi.query_conf_item",
                return_value={"content": {"kvstorecount": "10"}},
            ) as mock_dbconfig,
        ):
            has_backup, _, _, _, binlog_summary, _ = exercise._instance_has_backup(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert has_backup is True
        assert binlog_summary["count"] == 2
        mock_dbconfig.assert_called_once()
        call_kwargs = handler.query_binlog_from_bklog.call_args.kwargs
        assert call_kwargs["kvstorecount"] == "10"
        assert call_kwargs["tendis_type"] == ClusterType.TendisplusInstance.value

    def test_get_kvstorecount_returns_none_when_dbconfig_raises(self):
        """_get_kvstorecount swallows errors so the trigger doesn't crash on transient DBConfig issues."""
        cluster = _make_cluster_mock(ClusterType.TendisPredixyTendisplusCluster.value)

        with patch(f"{BASE_MODULE}.DBConfigApi.query_conf_item", side_effect=RuntimeError("boom")):
            assert _exercise_cls()._get_kvstorecount(cluster) is None


# ---------------------------------------------------------------------------
# 4) _validate_instance failure-kind dispatch
# ---------------------------------------------------------------------------


class TestValidateInstance:
    """Verify the failure_kind returned by _validate_instance maps each failure path correctly."""

    def test_backup_invalid_returns_backup_invalid_kind(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)

        with (
            patch.object(
                _exercise_cls(),
                "_instance_has_backup",
                return_value=(False, None, None, None, None, "no full backup"),
            ),
            patch(f"{BASE_MODULE}.TbTendisRollbackTasks.objects.filter") as mock_temp_filter,
            patch(f"{BASE_MODULE}.ClusterOperateRecord.objects.has_exclusive_operations_with_lock", return_value=[]),
            patch.object(_exercise_cls(), "_recent_master_slave_switch_hours", return_value=None),
        ):
            mock_temp_filter.return_value.exists.return_value = False
            (
                is_valid,
                full_backup,
                days_used,
                rtp,
                binlog_summary,
                fail_reason,
                failure_kind,
            ) = exercise._validate_instance(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert is_valid is False
        assert failure_kind == _failure_kind().BACKUP_INVALID
        assert full_backup is None and days_used is None and rtp is None and binlog_summary is None
        assert fail_reason and "no full backup" in fail_reason

    def test_backup_missing_after_recent_switch_returns_env_skipped(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)
        backup_check_instance = SimpleNamespace(ip_port="3.3.3.3:30000")

        with (
            patch.object(
                _exercise_cls(),
                "_instance_has_backup",
                return_value=(False, None, None, None, None, "no full backup"),
            ),
            patch(f"{BASE_MODULE}.TbTendisRollbackTasks.objects.filter") as mock_temp_filter,
            patch(f"{BASE_MODULE}.ClusterOperateRecord.objects.has_exclusive_operations_with_lock", return_value=[]),
            patch.object(_exercise_cls(), "_recent_master_slave_switch_hours", return_value=6),
        ):
            mock_temp_filter.return_value.exists.return_value = False
            (
                is_valid,
                full_backup,
                days_used,
                rtp,
                binlog_summary,
                fail_reason,
                failure_kind,
            ) = exercise._validate_instance(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
                backup_check_instance=backup_check_instance,
            )

        assert is_valid is False
        assert failure_kind == _failure_kind().ENV_SKIPPED
        assert full_backup is None and days_used is None and rtp is None and binlog_summary is None
        assert "possible recent master-slave switch" in fail_reason
        assert "6h ago" in fail_reason
        assert "backup file may be missing" in fail_reason

    def test_recent_master_slave_switch_uses_latest_receiver_tuple(self):
        tuple_qs = MagicMock()
        tuple_qs.order_by.return_value.first.return_value = SimpleNamespace(
            create_at=timezone.now() - timedelta(seconds=1)
        )
        slave_instance = SimpleNamespace(as_receiver=tuple_qs)

        switch_hours = _exercise_cls()._recent_master_slave_switch_hours(slave_instance)

        assert switch_hours == 0
        tuple_qs.order_by.assert_called_once_with("-create_at")

    def test_recent_master_slave_switch_returns_none_without_receiver_tuple(self):
        tuple_qs = MagicMock()
        tuple_qs.order_by.return_value.first.return_value = None
        slave_instance = SimpleNamespace(as_receiver=tuple_qs)

        assert _exercise_cls()._recent_master_slave_switch_hours(slave_instance) is None
        tuple_qs.order_by.assert_called_once_with("-create_at")

    def test_temp_instance_present_returns_env_skipped(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)

        temp_qs = MagicMock()
        temp_qs.exists.return_value = True

        with (
            patch.object(_exercise_cls(), "_instance_has_backup") as mock_has_backup,
            patch(f"{BASE_MODULE}.TbTendisRollbackTasks") as mock_temp_model,
        ):
            mock_temp_model.objects.filter.return_value = temp_qs

            is_valid, _, _, _, _, fail_reason, failure_kind = exercise._validate_instance(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert is_valid is False
        assert failure_kind == _failure_kind().ENV_SUPPRESSED
        assert "temp instances" in fail_reason
        mock_has_backup.assert_not_called()

    def test_exclusive_ticket_returns_env_suppressed(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)

        temp_qs = MagicMock()
        temp_qs.exists.return_value = False

        exclusive_ticket = SimpleNamespace(ticket_type="REDIS_DATA_STRUCTURE", id=999)
        exclusive_infos = [{"exclusive_ticket": exclusive_ticket, "root_id": "root-1"}]

        with (
            patch.object(_exercise_cls(), "_instance_has_backup") as mock_has_backup,
            patch(f"{BASE_MODULE}.TbTendisRollbackTasks") as mock_temp_model,
            patch(
                f"{BASE_MODULE}.ClusterOperateRecord.objects.has_exclusive_operations_with_lock",
                return_value=exclusive_infos,
            ) as mock_exclusive,
        ):
            mock_temp_model.objects.filter.return_value = temp_qs

            is_valid, _, _, _, _, fail_reason, failure_kind = exercise._validate_instance(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1],
            )

        assert is_valid is False
        assert failure_kind == _failure_kind().ENV_SUPPRESSED
        assert "exclusive active tickets" in fail_reason and "999" in fail_reason
        mock_exclusive.assert_called_once()
        mock_has_backup.assert_not_called()

    def test_all_clear_returns_valid(self):
        exercise = _make_exercise()
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)

        rtp = timezone.now() + timedelta(hours=1)
        binlog_summary = {"count": 5, "total_size_bytes": 1234}
        full_backup = _make_full_backup_log()
        backup_ok = (True, full_backup, 3, rtp, binlog_summary, None)

        temp_qs = MagicMock()
        temp_qs.exists.return_value = False

        with (
            patch.object(_exercise_cls(), "_instance_has_backup", return_value=backup_ok),
            patch(f"{BASE_MODULE}.TbTendisRollbackTasks") as mock_temp_model,
            patch(f"{BASE_MODULE}.ClusterOperateRecord.objects.has_exclusive_operations_with_lock", return_value=[]),
        ):
            mock_temp_model.objects.filter.return_value = temp_qs

            (
                is_valid,
                returned_full_backup,
                days_used,
                returned_rtp,
                returned_binlog_summary,
                fail_reason,
                failure_kind,
            ) = exercise._validate_instance(
                instance_ip="3.3.3.3",
                instance_port=30000,
                cluster=cluster,
                rollback_days=[1, 3, 7],
            )

        assert is_valid is True
        assert failure_kind is None
        assert fail_reason is None
        assert returned_full_backup is full_backup
        assert days_used == 3
        assert returned_rtp == rtp
        assert returned_binlog_summary is binlog_summary

    def test_datetime2str_works_on_returned_rtp(self):
        """Sanity: the recovery_time_point produced for ticket creation can be serialized."""
        rtp = timezone.now() + timedelta(hours=1)
        # Should not raise (aware datetime)
        assert isinstance(datetime2str(rtp), str)


# ---------------------------------------------------------------------------
# 5) start() report creation behavior
# ---------------------------------------------------------------------------


class TestStartReportSuppression:
    """Verify start() skips noisy report rows only for explicitly suppressed failures."""

    @staticmethod
    def _selected_item():
        cluster = _make_cluster_mock(ClusterType.TwemproxyTendisSSDInstance.value)
        instance = SimpleNamespace(
            machine=SimpleNamespace(ip="3.3.3.3"),
            port=30000,
            ip_port="3.3.3.3:30000",
        )
        return {"cluster": cluster, "instance": instance, "backup_check_instance": instance}

    def test_start_does_not_create_report_for_suppressed_skip(self):
        exercise = _make_exercise(enabled=True)
        selected_item = self._selected_item()

        with (
            patch.object(exercise, "_pick_target_instances", return_value=([selected_item], [])),
            patch.object(
                exercise,
                "_validate_instance",
                return_value=(False, None, None, None, None, "cluster busy", _failure_kind().ENV_SUPPRESSED),
            ),
            patch.object(exercise, "_create_report") as mock_create_report,
        ):
            exercise.start()

        mock_create_report.assert_not_called()

    def test_start_creates_report_for_backup_invalid(self):
        exercise = _make_exercise(enabled=True)
        selected_item = self._selected_item()
        report = MagicMock()

        with (
            patch.object(exercise, "_pick_target_instances", return_value=([selected_item], [])),
            patch.object(
                exercise,
                "_validate_instance",
                return_value=(False, None, None, None, None, "missing backup", _failure_kind().BACKUP_INVALID),
            ),
            patch.object(exercise, "_create_report", return_value=report) as mock_create_report,
        ):
            exercise.start()

        mock_create_report.assert_called_once_with(selected_item["cluster"], selected_item["instance"])
        report.mark.assert_called_once_with(
            TaskStage.BACKUP_INVALID,
            task_message=report.mark.call_args.kwargs["task_message"],
        )
        assert "missing backup" in report.mark.call_args.kwargs["task_message"]


# ---------------------------------------------------------------------------
# 6) SPECIFIED mode dispatch and discovery
# ---------------------------------------------------------------------------


class TestGetSpecifiedInstancesDomainsFilter:
    """domains + specified_bizs allowlist filtering."""

    def test_filters_domains_by_bizs(self):
        """Domains whose cluster bk_biz_id is not in specified_bizs are skipped."""
        in_biz = _fake_cluster(1, bk_biz_id=10, immute_domain="a.example.com")
        out_biz = _fake_cluster(2, bk_biz_id=99, immute_domain="b.example.com")
        domain_to_cluster = {"a.example.com": in_biz, "b.example.com": out_biz}

        exercise = _make_exercise(
            specified_domains=["a.example.com", "b.example.com"],
            specified_bizs=[10, 11],
        )

        with (
            patch(
                f"{BASE_MODULE}.Cluster.objects.get",
                side_effect=lambda immute_domain: domain_to_cluster[immute_domain],
            ),
            patch.object(
                _exercise_cls(),
                "_resolve_specified_cluster",
                side_effect=lambda cluster: _fake_selection(cluster),
            ),
        ):
            selected, skipped = exercise._get_specified_instances(num=10)

        assert [item["cluster"] for item in selected] == [in_biz]
        assert [cluster for cluster, _msg in skipped] == [out_biz]

    def test_filters_domains_by_bk_cloud_ids(self):
        """Domains outside bk_cloud_ids are skipped even when explicitly configured."""
        in_cloud = _fake_cluster(1, bk_biz_id=10, bk_cloud_id=0, immute_domain="a.example.com")
        out_cloud = _fake_cluster(2, bk_biz_id=10, bk_cloud_id=2000000, immute_domain="b.example.com")
        domain_to_cluster = {"a.example.com": in_cloud, "b.example.com": out_cloud}

        exercise = _make_exercise(
            specified_domains=["a.example.com", "b.example.com"],
            bk_cloud_ids=[0],
        )

        with (
            patch(
                f"{BASE_MODULE}.Cluster.objects.get",
                side_effect=lambda immute_domain: domain_to_cluster[immute_domain],
            ),
            patch.object(
                _exercise_cls(),
                "_resolve_specified_cluster",
                side_effect=lambda cluster: _fake_selection(cluster),
            ),
        ):
            selected, skipped = exercise._get_specified_instances(num=10)

        assert [item["cluster"] for item in selected] == [in_cloud]
        assert [cluster for cluster, _msg in skipped] == [out_cloud]
        assert "bk_cloud_id" in skipped[0][1]

    def test_no_bizs_keeps_legacy_behavior(self):
        """When specified_bizs is unset, every listed domain is selected (legacy)."""
        c1 = _fake_cluster(1, bk_biz_id=10, immute_domain="a.example.com")
        c2 = _fake_cluster(2, bk_biz_id=99, immute_domain="b.example.com")
        domain_to_cluster = {"a.example.com": c1, "b.example.com": c2}

        exercise = _make_exercise(specified_domains=["a.example.com", "b.example.com"])

        with (
            patch(
                f"{BASE_MODULE}.Cluster.objects.get",
                side_effect=lambda immute_domain: domain_to_cluster[immute_domain],
            ),
            patch.object(
                _exercise_cls(),
                "_resolve_specified_cluster",
                side_effect=lambda cluster: _fake_selection(cluster),
            ),
        ):
            selected, skipped = exercise._get_specified_instances(num=10)

        assert [item["cluster"] for item in selected] == [c1, c2]
        assert skipped == []

    def test_records_skip_when_no_slave(self):
        """A domain whose cluster has no slave is recorded as skipped."""
        c1 = _fake_cluster(1, bk_biz_id=10, immute_domain="a.example.com")

        exercise = _make_exercise(specified_domains=["a.example.com"])

        with (
            patch(f"{BASE_MODULE}.Cluster.objects.get", return_value=c1),
            patch.object(_exercise_cls(), "_resolve_specified_cluster", return_value=None),
        ):
            selected, skipped = exercise._get_specified_instances(num=10)

        assert selected == []
        assert [cluster for cluster, _msg in skipped] == [c1]


class TestGetSpecifiedInstancesBizDiscovery:
    """Empty domains + specified_bizs discovery."""

    def test_discovers_clusters_in_bizs(self):
        """With no domains but specified_bizs set, discover ONLINE clusters in those bizs."""
        c1 = _fake_cluster(1, bk_biz_id=10, immute_domain="a.example.com")
        c2 = _fake_cluster(2, bk_biz_id=11, immute_domain="b.example.com")

        exercise = _make_exercise(specified_bizs=[10, 11])

        queryset = MagicMock()
        queryset.filter.return_value = queryset
        queryset.values_list.return_value = [(1, 10), (2, 11)]

        with (
            patch.object(
                _exercise_cls(),
                "_rollback_exercise_candidate_queryset",
                return_value=queryset,
            ),
            patch.object(
                _exercise_cls(),
                "_weighted_random_selection",
                return_value=[1, 2],
            ),
            patch(
                f"{BASE_MODULE}.Cluster.objects.get",
                side_effect=lambda id: {1: c1, 2: c2}[id],
            ),
            patch.object(
                _exercise_cls(),
                "_resolve_specified_cluster",
                side_effect=lambda cluster: _fake_selection(cluster),
            ),
        ):
            selected, skipped = exercise._get_specified_instances(num=5)

        queryset.filter.assert_called_once_with(bk_biz_id__in={10, 11})
        assert [item["cluster"] for item in selected] == [c1, c2]
        assert skipped == []

    def test_discovery_respects_num_cap(self):
        """Discovery selects min(num, candidate_count) via weighted sampling."""
        exercise = _make_exercise(specified_bizs=[10])

        queryset = MagicMock()
        queryset.filter.return_value = queryset
        queryset.values_list.return_value = [(i, 10) for i in range(1, 6)]

        captured = {}

        def fake_weighted(pairs, count):
            captured["count"] = count
            return [pair[0] for pair in pairs[:count]]

        with (
            patch.object(
                _exercise_cls(),
                "_rollback_exercise_candidate_queryset",
                return_value=queryset,
            ),
            patch.object(
                _exercise_cls(),
                "_weighted_random_selection",
                side_effect=fake_weighted,
            ),
            patch(
                f"{BASE_MODULE}.Cluster.objects.get",
                side_effect=lambda id: _fake_cluster(id, 10, f"d{id}.example.com"),
            ),
            patch.object(
                _exercise_cls(),
                "_resolve_specified_cluster",
                side_effect=lambda cluster: _fake_selection(cluster),
            ),
        ):
            selected, _skipped = exercise._get_specified_instances(num=2)

        assert captured["count"] == 2
        assert len(selected) == 2

    def test_discovery_empty_returns_empty(self):
        """When no candidates exist in specified_bizs, return empty without raising."""
        exercise = _make_exercise(specified_bizs=[10])

        queryset = MagicMock()
        queryset.filter.return_value = queryset
        queryset.values_list.return_value = []

        with patch.object(
            _exercise_cls(),
            "_rollback_exercise_candidate_queryset",
            return_value=queryset,
        ):
            selected, skipped = exercise._get_specified_instances(num=5)

        assert selected == []
        assert skipped == []


# ---------------------------------------------------------------------------
# 6) Weighted random selection strategy
# ---------------------------------------------------------------------------


class TestWeightedSampleWithoutReplacement:
    """Edge cases and weight-bias determinism for the A-Res sampling helper."""

    def test_count_ge_len_returns_all_items_copy(self):
        exercise = _make_exercise()
        items = [1, 2, 3]
        weights = [1.0, 1.0, 1.0]

        result = exercise._weighted_sample_without_replacement(items, weights, len(items))

        assert result == items
        assert result is not items  # Defensive copy

    def test_count_greater_than_len_returns_all_items(self):
        exercise = _make_exercise()
        items = [1, 2]
        weights = [1.0, 1.0]

        assert exercise._weighted_sample_without_replacement(items, weights, 10) == items

    def test_count_zero_returns_empty(self):
        exercise = _make_exercise()
        items = [1, 2, 3]
        weights = [1.0, 1.0, 1.0]

        # count == 0 with non-empty items goes through the explicit `if count == 0` branch.
        assert exercise._weighted_sample_without_replacement(items, weights, 0) == []

    def test_zero_or_negative_weights_do_not_crash(self):
        """Zero / negative weights are replaced by 1e-10 so log() never explodes."""
        exercise = _make_exercise()
        items = [1, 2, 3, 4]
        weights = [0.0, -1.0, 1.0, 5.0]

        result = exercise._weighted_sample_without_replacement(items, weights, 2)

        assert len(result) == 2
        assert set(result).issubset(set(items))

    def test_heavy_weight_dominates_under_seed_sweep(self):
        """A 1000x-weighted item should win count=1 selection on virtually every seed."""
        exercise = _make_exercise()
        items = [10, 20, 30, 40]
        weights = [1.0, 1.0, 100.0, 1.0]
        heavy_item = 30

        wins = 0
        trials = 50
        for seed in range(trials):
            random.seed(seed)
            picked = exercise._weighted_sample_without_replacement(items, weights, 1)
            if picked == [heavy_item]:
                wins += 1

        # Without weighting this would average ~12/50 (25%). With a 1000x edge it should
        # essentially always win; we leave a small safety margin against floating-point edges.
        assert wins >= 45, f"heavy item picked only {wins}/{trials} seeds"


class TestWeightedRandomSelection:
    """Verify the multiplicative weight strategy in _weighted_random_selection."""

    @staticmethod
    def _capture_weights(exercise):
        """Patch _weighted_sample_without_replacement on the instance to capture the weights arg."""
        captured: dict = {}

        def _fake(items, weights, count):
            captured["items"] = list(items)
            captured["weights"] = list(weights)
            captured["count"] = count
            return list(items[:count])

        return captured, patch.object(exercise, "_weighted_sample_without_replacement", side_effect=_fake)

    @staticmethod
    def _patch_reports(failed: set, not_exercised: set):
        """Patch Report.get_previously_failed_clusters / get_not_exercised_clusters at the source module."""
        return (
            patch(
                f"{BASE_MODULE}.Report.get_previously_failed_clusters",
                return_value=(failed, MagicMock(name="failed_qs")),
            ),
            patch(
                f"{BASE_MODULE}.Report.get_not_exercised_clusters",
                return_value=(not_exercised, MagicMock(name="not_exercised_qs")),
            ),
        )

    def test_default_multipliers_combined(self):
        """Cluster in all three sets gets weight 2.0 * 3.0 * 2.0 = 12.0; baseline stays 1.0."""
        # ids: 1 -> all-three, 2 -> none
        exercise = _make_exercise(bizs_high_priority=[10])
        captured, patch_sample = self._capture_weights(exercise)
        patch_failed, patch_not_ex = self._patch_reports(failed={1}, not_exercised={1})

        with patch_failed, patch_not_ex, patch_sample:
            exercise._weighted_random_selection([(1, 10), (2, 99)], count=2)

        assert captured["items"] == [1, 2]
        assert captured["weights"] == pytest.approx([12.0, 1.0])

    def test_partial_overlaps(self):
        """High-priority only -> 2.0, failed only -> 3.0, not-exercised only -> 2.0."""
        # 1 high-priority biz only, 2 previously failed only, 3 not exercised only, 4 none
        exercise = _make_exercise(bizs_high_priority=[10])
        captured, patch_sample = self._capture_weights(exercise)
        patch_failed, patch_not_ex = self._patch_reports(failed={2}, not_exercised={3})

        with patch_failed, patch_not_ex, patch_sample:
            exercise._weighted_random_selection(
                [(1, 10), (2, 99), (3, 99), (4, 99)],
                count=4,
            )

        assert captured["weights"] == pytest.approx([2.0, 3.0, 2.0, 1.0])

    def test_bizs_high_priority_none_does_not_raise(self):
        """The `or []` fallback at the call site allows None/unset bizs_high_priority."""
        exercise = _make_exercise()  # default: bizs_high_priority is None
        captured, patch_sample = self._capture_weights(exercise)
        patch_failed, patch_not_ex = self._patch_reports(failed=set(), not_exercised=set())

        with patch_failed, patch_not_ex, patch_sample:
            exercise._weighted_random_selection([(1, 10)], count=1)

        assert captured["weights"] == pytest.approx([1.0])

    def test_empty_input_short_circuits_before_report_calls(self):
        """Empty cluster_id_biz_pairs returns [] without touching Report or sampling."""
        exercise = _make_exercise()
        captured, patch_sample = self._capture_weights(exercise)

        with (
            patch(f"{BASE_MODULE}.Report.get_previously_failed_clusters") as mock_failed,
            patch(f"{BASE_MODULE}.Report.get_not_exercised_clusters") as mock_not_ex,
            patch_sample,
        ):
            result = exercise._weighted_random_selection([], count=5)

        assert result == []
        mock_failed.assert_not_called()
        mock_not_ex.assert_not_called()
        assert captured == {}  # _weighted_sample_without_replacement was not invoked

    def test_custom_multipliers_are_honored(self):
        """Overriding weight_multiplier_high_priority_biz changes the captured weight."""
        exercise = _make_exercise(
            bizs_high_priority=[10],
            weight_multiplier_high_priority_biz=5.0,
        )
        captured, patch_sample = self._capture_weights(exercise)
        patch_failed, patch_not_ex = self._patch_reports(failed=set(), not_exercised=set())

        with patch_failed, patch_not_ex, patch_sample:
            exercise._weighted_random_selection([(1, 10), (2, 99)], count=2)

        assert captured["weights"] == pytest.approx([5.0, 1.0])
