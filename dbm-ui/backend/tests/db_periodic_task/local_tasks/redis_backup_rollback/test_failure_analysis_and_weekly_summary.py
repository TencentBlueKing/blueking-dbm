# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Unit tests for Redis rollback-exercise AI failure analysis and weekly summary.

Lazy-import helpers avoid triggering local_tasks package registration (DB writes)
at pytest collection time — same convention as sibling rollback-exercise tests.
"""
import json
import re
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report

pytestmark = pytest.mark.django_db

FAILURE_MODULE = "backend.db_services.redis.rollback.failure_analysis"
WEEKLY_MODULE = "backend.db_periodic_task.local_tasks.redis_backup_rollback.weekly_ai_summary"


def _failure():
    from backend.db_services.redis.rollback import failure_analysis as mod

    return mod


def _weekly():
    from backend.db_periodic_task.local_tasks.redis_backup_rollback import weekly_ai_summary as mod

    return mod


def _aware(year, month, day, hour=12, minute=0):
    """Build an aware datetime in the active Django timezone."""
    return timezone.make_aware(datetime(year, month, day, hour, minute, 0))


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


class TestGetWeekWindow:
    def test_monday_uses_last_and_this_sunday_noon(self):
        weekly = _weekly()
        # Monday 2026-08-10 10:00 -> [Sunday 2026-08-02 12:00, Sunday 2026-08-09 12:00)
        now = _aware(2026, 8, 10, 10, 0)
        start, end = weekly.get_week_window(now)
        assert timezone.localtime(start).strftime("%Y-%m-%d %H:%M") == "2026-08-02 12:00"
        assert timezone.localtime(end).strftime("%Y-%m-%d %H:%M") == "2026-08-09 12:00"

    def test_before_sunday_noon_falls_back_one_week(self):
        weekly = _weekly()
        # Sunday 2026-08-09 10:00 (before candidate init) -> [2026-07-26 12:00, 2026-08-02 12:00)
        now = _aware(2026, 8, 9, 10, 0)
        start, end = weekly.get_week_window(now)
        assert timezone.localtime(start).strftime("%Y-%m-%d %H:%M") == "2026-07-26 12:00"
        assert timezone.localtime(end).strftime("%Y-%m-%d %H:%M") == "2026-08-02 12:00"

    def test_previous_window_has_equal_length(self):
        weekly = _weekly()
        start, end = _aware(2026, 8, 2, 12, 0), _aware(2026, 8, 9, 12, 0)
        prev_start, prev_end = weekly.get_previous_week_window(start, end)
        assert prev_end == start
        assert (prev_end - prev_start) == (end - start)


# ---------------------------------------------------------------------------
# Category parsing / content cutting
# ---------------------------------------------------------------------------


class TestParseAndCut:
    def test_parse_category_from_ai_block(self):
        weekly = _weekly()
        msg = "old log\n[AI失败分析] 2026-08-07 10:00:00\n原因分类: 构造流程失败\n诊断: x\n建议: y"
        assert weekly._parse_failure_category(msg) == "构造流程失败"

    def test_parse_category_missing_analysis(self):
        weekly = _weekly()
        assert "未分析" in weekly._parse_failure_category("plain failure log")

    def test_parse_diagnosis_from_ai_block(self):
        weekly = _weekly()
        msg = "old log\n[AI失败分析] 2026-08-07 10:00:00\n原因分类: 构造流程失败\n诊断: child boom\n建议: y"
        assert weekly._parse_failure_diagnosis(msg) == "child boom"

    def test_parse_diagnosis_prefers_last_block(self):
        weekly = _weekly()
        msg = "[AI失败分析] t1\n原因分类: 其他\n诊断: first\n建议: a\n" "[AI失败分析] t2\n原因分类: API调用错误\n诊断: second\n建议: b"
        assert weekly._parse_failure_diagnosis(msg) == "second"

    def test_parse_diagnosis_sentinel_without_line(self):
        weekly = _weekly()
        msg = "[AI失败分析] t\n原因分类: 其他\n建议: y"
        assert weekly._parse_failure_diagnosis(msg) == ""

    def test_parse_diagnosis_missing_analysis(self):
        weekly = _weekly()
        assert weekly._parse_failure_diagnosis("plain failure log") == ""

    def test_parse_ignores_cleanup_logs_after_closed_ai_block(self):
        weekly = _weekly()
        msg = (
            "timeline\n"
            "[AI失败分析] 2026-08-10 14:43:43\n"
            "原因分类: 执行器错误\n"
            "诊断: 模板变量未被渲染\n"
            "建议: 修复 databases 渲染\n"
            "AI耗时: 25.5s\n"
            "[/AI失败分析]\n"
            "[2026-08-10 14:48:38] [INFO]: Step 1/4: Collecting cleanup targets\n"
            "诊断: should-not-win\n"
            "原因分类: 其他\n"
        )
        assert weekly._parse_failure_category(msg) == "执行器错误"
        assert weekly._parse_failure_diagnosis(msg) == "模板变量未被渲染"

    def test_parse_legacy_block_without_end_sentinel_caps_window(self):
        weekly = _weekly()
        # Legacy: no [/AI失败分析]. Cleanup lines after the 8-line window must not win.
        noise = "\n".join([f"cleanup line {i}" for i in range(20)])
        msg = (
            "timeline\n"
            "[AI失败分析] 2026-08-10 14:43:43\n"
            "原因分类: 执行器错误\n"
            "诊断: real diagnosis\n"
            "建议: fix it\n"
            "AI耗时: 1.0s\n"
            f"{noise}\n"
            "原因分类: 其他\n"
            "诊断: fake from cleanup\n"
        )
        assert weekly._parse_failure_category(msg) == "执行器错误"
        assert weekly._parse_failure_diagnosis(msg) == "real diagnosis"

    def test_cut_content_splits_long_message(self):
        weekly = _weekly()
        lines = [f"line-{i}-" + ("x" * 80) for i in range(30)]
        content = "\n".join(lines)
        chunks = weekly.cut_content(content, max_len=200)
        assert len(chunks) > 1
        assert all(len(c) <= 200 for c in chunks)
        assert "".join(chunks) == content

    def test_cut_content_hard_splits_single_oversized_line(self):
        weekly = _weekly()
        content = "x" * 450
        chunks = weekly.cut_content(content, max_len=200)
        assert [len(chunk) for chunk in chunks] == [200, 200, 50]
        assert "".join(chunks) == content


# ---------------------------------------------------------------------------
# Stage-aware log source
# ---------------------------------------------------------------------------


class TestResolveFlowRootId:
    def test_rollback_failed_uses_rollback_flow_id(self):
        failure = _failure()
        report = SimpleNamespace(
            task_stage=TaskStage.ROLLBACK_FAILED,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="del-root",
        )
        assert failure._resolve_flow_root_id(report) == "rb-root"

    def test_cleanup_failed_prefers_delete_flow_id(self):
        failure = _failure()
        report = SimpleNamespace(
            task_stage=TaskStage.CLEANUP_FAILED,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="del-root",
        )
        assert failure._resolve_flow_root_id(report) == "del-root"

    def test_cleanup_failed_falls_back_to_rollback_flow_id(self):
        failure = _failure()
        report = SimpleNamespace(
            task_stage=TaskStage.CLEANUP_FAILED,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="",
        )
        assert failure._resolve_flow_root_id(report) == "rb-root"

    def test_generator_stage_has_no_flow_id(self):
        failure = _failure()
        report = SimpleNamespace(
            task_stage=TaskStage.BACKUP_INVALID,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="del-root",
        )
        assert failure._resolve_flow_root_id(report) == ""

    def test_explicit_stage_overrides_report_stage(self):
        failure = _failure()
        # report still at ROLLBACK_SUCCEEDED; resolve as-if CLEANUP_FAILED is about to be marked
        report = SimpleNamespace(
            task_stage=TaskStage.ROLLBACK_SUCCEEDED,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="del-root",
        )
        assert failure._resolve_flow_root_id(report, stage=TaskStage.CLEANUP_FAILED) == "del-root"
        assert failure._resolve_flow_root_id(report, stage=TaskStage.ROLLBACK_FAILED) == "rb-root"


# ---------------------------------------------------------------------------
# embed_failed_node_logs
# ---------------------------------------------------------------------------


class TestEmbedFailedNodeLogs:
    def _report(self, **overrides):
        base = dict(
            id=1,
            task_stage=TaskStage.ROLLBACK_STARTED,
            rollback_flow_obj_id="rb-root",
            delete_flow_obj_id="del-root",
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_non_flow_stage_unchanged(self):
        failure = _failure()
        report = self._report()
        msg = "timeline only"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs") as mock_logs:
            out = failure.embed_failed_node_logs(msg, report, TaskStage.BACKUP_INVALID)
        assert out == msg
        mock_logs.assert_not_called()

    def test_sentinel_already_present_is_idempotent(self):
        failure = _failure()
        report = self._report()
        msg = f"timeline\n{failure.FAILED_NODE_LOGS_SENTINEL} root_id=rb-root\n    [ERROR] old"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs") as mock_logs:
            out = failure.embed_failed_node_logs(msg, report, TaskStage.ROLLBACK_FAILED)
        assert out == msg
        mock_logs.assert_not_called()

    def test_no_root_id_unchanged(self):
        failure = _failure()
        report = self._report(rollback_flow_obj_id="", delete_flow_obj_id="")
        msg = "timeline"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs") as mock_logs:
            out = failure.embed_failed_node_logs(msg, report, TaskStage.ROLLBACK_FAILED)
        assert out == msg
        mock_logs.assert_not_called()

    def test_empty_logs_unchanged(self):
        failure = _failure()
        report = self._report()
        msg = "timeline"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs", return_value=""):
            out = failure.embed_failed_node_logs(msg, report, TaskStage.ROLLBACK_FAILED)
        assert out == msg

    def test_fetch_exception_unchanged(self):
        failure = _failure()
        report = self._report()
        msg = "timeline"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs", side_effect=RuntimeError("bklog down")):
            out = failure.embed_failed_node_logs(msg, report, TaskStage.ROLLBACK_FAILED)
        assert out == msg

    def test_happy_path_appends_indented_block(self):
        failure = _failure()
        report = self._report()
        msg = "timeline line"
        raw_logs = "failed_node: 回档 (n1) version=v1 status=FAILED pick=failed_or_revoked\n[ERROR] boom"
        with patch(f"{FAILURE_MODULE}.get_last_failed_node_logs", return_value=raw_logs) as mock_logs:
            out = failure.embed_failed_node_logs(msg, report, TaskStage.ROLLBACK_FAILED)

        mock_logs.assert_called_once_with("rb-root", max_chars=failure._MAX_EMBEDDED_LOG_CHARS)
        assert failure.FAILED_NODE_LOGS_SENTINEL in out
        assert "root_id=rb-root" in out
        assert "    failed_node: 回档 (n1)" in out
        assert "    [ERROR] boom" in out
        assert out.startswith("timeline line\n")

    def test_cleanup_failed_uses_delete_flow_id(self):
        failure = _failure()
        report = self._report()
        with patch(
            f"{FAILURE_MODULE}.get_last_failed_node_logs",
            return_value="failed_node: cleanup (n2)\n[ERROR] rm failed",
        ) as mock_logs:
            out = failure.embed_failed_node_logs("", report, TaskStage.CLEANUP_FAILED)

        mock_logs.assert_called_once_with("del-root", max_chars=failure._MAX_EMBEDDED_LOG_CHARS)
        assert "root_id=del-root" in out
        assert out.startswith(failure.FAILED_NODE_LOGS_SENTINEL)


# ---------------------------------------------------------------------------
# Aggregation (DB)
# ---------------------------------------------------------------------------


class TestAggregateExerciseStats(TestCase):
    databases = {"default", "report_db"}

    def setUp(self):
        Report.objects.all().delete()
        self.start = timezone.now() - timedelta(days=3)
        self.end = timezone.now() + timedelta(hours=1)

    def tearDown(self):
        Report.objects.all().delete()

    def _create(self, **overrides):
        kwargs = dict(
            bk_biz_id=100,
            bk_cloud_id=0,
            cluster_id=10001,
            cluster_domain="cache-a.dba.db",
            cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
            instance_ip="1.1.1.1",
            instance_port=30000,
            redis_version="6.2.7",
            task_stage=TaskStage.DONE,
            creator="system",
            updater="system",
        )
        kwargs.update(overrides)
        return Report.objects.create(**kwargs)

    def test_counts_and_category_distribution(self):
        weekly = _weekly()
        failure = _failure()

        self._create(cluster_id=1, cluster_domain="ok.dba.db", task_stage=TaskStage.DONE)
        self._create(cluster_id=2, cluster_domain="skip.dba.db", task_stage=TaskStage.SKIPPED)
        self._create(
            cluster_id=3,
            cluster_domain="fail-a.dba.db",
            task_stage=TaskStage.ROLLBACK_FAILED,
            task_message=f"err\n{failure.AI_ANALYSIS_SENTINEL} t\n原因分类: 构造流程失败\n诊断: x\n建议: y",
            instance_ip="1.1.1.1",
        )
        self._create(
            cluster_id=4,
            cluster_domain="fail-a.dba.db",
            task_stage=TaskStage.ROLLBACK_FAILED,
            task_message=f"err\n{failure.AI_ANALYSIS_SENTINEL} t\n原因分类: 构造流程失败\n诊断: x\n建议: y",
            instance_ip="1.1.1.9",
        )
        self._create(
            cluster_id=5,
            cluster_domain="fail-b.dba.db",
            task_stage=TaskStage.BACKUP_INVALID,
            task_message="no backup",
            instance_ip="2.2.2.2",
        )

        stats = weekly.aggregate_exercise_stats(self.start, self.end)
        assert stats["total"] == 5
        assert stats["done"] == 1
        assert stats["skipped"] == 1
        assert stats["failed"] == 3
        assert stats["failure_category_distribution"]["构造流程失败"] == 2
        assert stats["missing_analysis_count"] == 1
        assert any(item["cluster_domain"] == "fail-a.dba.db" for item in stats["repeat_offender_clusters"])
        assert len(stats["failure_cases"]) == 3
        assert any(c.endswith("构造流程失败 | x") for c in stats["failure_cases"])
        # Unanalyzed failures keep the bare category line (no diagnosis suffix).
        assert any("backup_invalid" in c and "|" not in c for c in stats["failure_cases"])


# ---------------------------------------------------------------------------
# Enqueue / analyze idempotency
# ---------------------------------------------------------------------------


class TestFailureAnalysisEnqueueAndIdempotency(TestCase):
    databases = {"default", "report_db"}

    def setUp(self):
        Report.objects.all().delete()

    def tearDown(self):
        Report.objects.all().delete()

    def _create_failed(self, **overrides):
        kwargs = dict(
            bk_biz_id=100,
            bk_cloud_id=0,
            cluster_id=10001,
            cluster_domain="cache-fail.dba.db",
            cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
            instance_ip="1.1.1.1",
            instance_port=30000,
            redis_version="6.2.7",
            task_stage=TaskStage.ROLLBACK_FAILED,
            task_message="Child pipeline failed",
            rollback_flow_obj_id="child-root-1",
            creator="system",
            updater="system",
        )
        kwargs.update(overrides)
        return Report.objects.create(**kwargs)

    @patch(f"{FAILURE_MODULE}.analyze_redis_rollback_exercise_failure.apply_async")
    @patch(f"{FAILURE_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_enqueue_when_ai_enabled(self, _mock_enabled, mock_apply):
        failure = _failure()
        report = self._create_failed()
        assert failure.enqueue_exercise_failure_analysis(report.id, countdown=10) is True
        mock_apply.assert_called_once()
        assert mock_apply.call_args.kwargs["countdown"] == 10

    @patch(f"{FAILURE_MODULE}.analyze_redis_rollback_exercise_failure.apply_async")
    @patch(f"{FAILURE_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_enqueue_noop_when_analysis_already_appended(self, _mock_enabled, mock_apply):
        failure = _failure()
        report = self._create_failed(task_message=f"{failure.AI_ANALYSIS_SENTINEL}\n原因分类: 配置")
        assert failure.enqueue_exercise_failure_analysis(report.id) is False
        mock_apply.assert_not_called()

    @patch(f"{FAILURE_MODULE}.analyze_redis_rollback_exercise_failure.apply_async")
    @patch(f"{FAILURE_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_enqueue_noop_when_report_not_failed(self, _mock_enabled, mock_apply):
        failure = _failure()
        report = self._create_failed(task_stage=TaskStage.DONE)
        assert failure.enqueue_exercise_failure_analysis(report.id) is False
        mock_apply.assert_not_called()

    @patch(f"{FAILURE_MODULE}.analyze_redis_rollback_exercise_failure.apply_async")
    @patch(f"{FAILURE_MODULE}.is_exercise_ai_analysis_enabled", return_value=False)
    def test_enqueue_noop_when_ai_disabled(self, _mock_enabled, mock_apply):
        failure = _failure()
        report = self._create_failed()
        assert failure.enqueue_exercise_failure_analysis(report.id) is False
        mock_apply.assert_not_called()

    @patch("backend.db_services.redis.rollback.config.RedisRollbackExerciseConfig.from_settings")
    def test_is_exercise_ai_analysis_enabled_requires_config_flag(self, mock_from_settings):
        failure = _failure()
        mock_from_settings.return_value = SimpleNamespace(ai_analysis_enabled=False)
        with patch.object(failure.env, "ENABLE_DBM_AI", True):
            assert failure.is_exercise_ai_analysis_enabled() is False

        mock_from_settings.return_value = SimpleNamespace(ai_analysis_enabled=True)
        with patch.object(failure.env, "ENABLE_DBM_AI", True):
            assert failure.is_exercise_ai_analysis_enabled() is True
        with patch.object(failure.env, "ENABLE_DBM_AI", False):
            assert failure.is_exercise_ai_analysis_enabled() is False

    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    def test_analyze_appends_sentinel_once(self, mock_ask):
        failure = _failure()
        embedded = (
            "Child pipeline failed\n"
            f"{failure.FAILED_NODE_LOGS_SENTINEL} root_id=child-root-1\n"
            "    failed_node: 回档 (n1)\n"
            "    [ERROR] boom"
        )
        report = self._create_failed(task_message=embedded)
        mock_ask.return_value = "原因分类: 构造流程失败\n诊断: 子流程 boom\n建议: 查看 child-root-1"

        failure.analyze_redis_rollback_exercise_failure.run(report.id)

        report.refresh_from_db()
        assert failure.AI_ANALYSIS_SENTINEL in report.task_message
        assert failure.AI_ANALYSIS_END_SENTINEL in report.task_message
        assert "构造流程失败" in report.task_message
        # Block is visually delimited with blank lines around the sentinels.
        assert f"\n{failure.AI_ANALYSIS_SENTINEL}" in report.task_message or report.task_message.startswith(
            failure.AI_ANALYSIS_SENTINEL
        )
        assert f"{failure.AI_ANALYSIS_END_SENTINEL}\n" in report.task_message or report.task_message.endswith(
            failure.AI_ANALYSIS_END_SENTINEL
        )
        cost_match = re.search(r"AI耗时: (\d+\.\d)s", report.task_message)
        assert cost_match, report.task_message
        assert float(cost_match.group(1)) >= 0.0
        # AI耗时 stays inside the closed block.
        end_pos = report.task_message.index(failure.AI_ANALYSIS_END_SENTINEL)
        assert cost_match.start() < end_pos
        first_msg = report.task_message
        assert mock_ask.call_count == 1
        params = mock_ask.call_args.kwargs["command_params"]
        assert "flow_error_logs" not in params
        assert failure.FAILED_NODE_LOGS_SENTINEL in params["task_message"]

        failure.analyze_redis_rollback_exercise_failure.run(report.id)

        report.refresh_from_db()
        assert report.task_message == first_msg
        assert report.task_message.count(failure.AI_ANALYSIS_SENTINEL) == 1
        assert mock_ask.call_count == 1

    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    def test_analyze_head_tail_truncates_task_message(self, mock_ask):
        failure = _failure()
        head = "HEAD-" + ("A" * 100)
        middle = "MID-" + ("B" * 15000)
        tail = "TAIL-" + ("C" * 100) + f"\n{failure.FAILED_NODE_LOGS_SENTINEL} root_id=x\n    [ERROR] boom"
        report = self._create_failed(task_message=head + middle + tail)
        mock_ask.return_value = "原因分类: 其他\n诊断: x\n建议: y"

        failure.analyze_redis_rollback_exercise_failure.run(report.id)

        params = mock_ask.call_args.kwargs["command_params"]
        tm = params["task_message"]
        assert tm.startswith("HEAD-")
        assert "中间截断" in tm
        assert "[ERROR] boom" in tm
        assert len(tm) <= failure._MAX_TASK_MESSAGE_CHARS + 80  # marker slack

    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    def test_analyze_agent_error_appends_failed_sentinel(self, mock_ask):
        failure = _failure()
        report = self._create_failed(task_message="Child pipeline failed")
        mock_ask.side_effect = RuntimeError("agent boom")

        failure.analyze_redis_rollback_exercise_failure.run(report.id)

        report.refresh_from_db()
        assert failure.AI_ANALYSIS_FAILED_SENTINEL in report.task_message
        assert "智能体调用失败" in report.task_message
        cost_match = re.search(r"AI耗时: (\d+\.\d)s", report.task_message)
        assert cost_match, report.task_message
        # Distinct sentinel keeps weekly stats from counting this as a real category.
        assert _weekly()._parse_failure_category(report.task_message) == "未分析"

    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    def test_analyze_strips_fence_with_language_tag(self, mock_ask):
        failure = _failure()
        report = self._create_failed(task_message="Child pipeline failed")
        mock_ask.return_value = "```markdown\n原因分类: 构造流程失败\n诊断: 子流程 boom\n```"

        failure.analyze_redis_rollback_exercise_failure.run(report.id)

        report.refresh_from_db()
        assert "markdown" not in report.task_message
        assert "```" not in report.task_message
        assert "构造流程失败" in report.task_message

    @patch(f"{FAILURE_MODULE}.enqueue_exercise_failure_analysis")
    def test_mark_failed_stage_triggers_enqueue(self, mock_enqueue):
        report = self._create_failed(task_stage=TaskStage.TASK_GENERATED, task_message="")
        report.mark(TaskStage.ROLLBACK_FAILED, task_message="failed")
        mock_enqueue.assert_called_once_with(report.id)

    @patch(f"{FAILURE_MODULE}.enqueue_exercise_failure_analysis")
    def test_mark_task_message_only_does_not_enqueue(self, mock_enqueue):
        report = self._create_failed()
        report.mark(task_message="append only")
        mock_enqueue.assert_not_called()


class TestGetLastFailedNodeLogs:
    def test_empty_root_id(self):
        failure = _failure()
        assert failure.get_last_failed_node_logs("") == ""

    def test_no_abnormal_node(self):
        failure = _failure()
        with patch(f"{FAILURE_MODULE}._pick_last_abnormal_flow_node", return_value=(None, "")):
            assert failure.get_last_failed_node_logs("root-x") == ""

    def test_formats_and_truncates_preferring_error_tail(self):
        failure = _failure()
        last_failed = SimpleNamespace(
            node_id="n1",
            version_id="v1",
            status="REVOKED",
            started_at=timezone.now(),
            updated_at=timezone.now(),
        )
        long_msg = "x" * 200

        with patch(
            f"{FAILURE_MODULE}._pick_last_abnormal_flow_node",
            return_value=(last_failed, "failed_or_revoked"),
        ), patch("backend.flow.engine.bamboo.engine.BambooEngine") as mock_engine_cls, patch(
            f"{FAILURE_MODULE}._fetch_node_logs_capped",
            return_value=[
                {"levelname": "INFO", "message": "start"},
                {"levelname": "ERROR", "message": long_msg},
            ],
        ):
            engine = mock_engine_cls.return_value
            engine.get_pipeline_tree.return_value = {
                "activities": {"n1": {"name": "回档节点"}},
            }

            text = failure.get_last_failed_node_logs("root-x", max_chars=120)

        assert "failed_node: 回档节点 (n1)" in text
        assert "status=REVOKED" in text
        # Tight budget keeps the ERROR (tail-truncated) and may drop the INFO head.
        assert "[ERROR]" in text
        assert "..." in text
        assert len(text) <= 120 + 5  # small slack for join

    def test_error_window_keeps_context_and_omits_head(self):
        failure = _failure()
        lines = [{"levelname": "INFO", "message": f"noise-{i}"} for i in range(20)]
        lines.append({"levelname": "INFO", "message": "before-err"})
        lines.append({"levelname": "ERROR", "message": "real-boom"})
        lines.append({"levelname": "INFO", "message": "after-err"})
        last_failed = SimpleNamespace(
            node_id="n1",
            version_id="v1",
            status="FAILED",
            started_at=timezone.now(),
            updated_at=timezone.now(),
        )
        with patch(
            f"{FAILURE_MODULE}._pick_last_abnormal_flow_node",
            return_value=(last_failed, "failed_or_revoked"),
        ), patch("backend.flow.engine.bamboo.engine.BambooEngine") as mock_engine_cls, patch(
            f"{FAILURE_MODULE}._fetch_node_logs_capped",
            return_value=lines,
        ):
            mock_engine_cls.return_value.get_pipeline_tree.return_value = {
                "activities": {"n1": {"name": "回档"}},
            }
            text = failure.get_last_failed_node_logs("root-x", max_chars=800)

        assert "[ERROR] real-boom" in text
        assert "before-err" in text
        assert "after-err" in text
        assert "省略" in text
        assert "noise-0" not in text

    def test_no_error_falls_back_to_tail(self):
        failure = _failure()
        lines = [{"levelname": "INFO", "message": f"step-{i}"} for i in range(30)]
        last_failed = SimpleNamespace(
            node_id="n1",
            version_id="v1",
            status="REVOKED",
            started_at=timezone.now(),
            updated_at=timezone.now(),
        )
        with patch(
            f"{FAILURE_MODULE}._pick_last_abnormal_flow_node",
            return_value=(last_failed, "failed_or_revoked"),
        ), patch("backend.flow.engine.bamboo.engine.BambooEngine") as mock_engine_cls, patch(
            f"{FAILURE_MODULE}._fetch_node_logs_capped",
            return_value=lines,
        ):
            mock_engine_cls.return_value.get_pipeline_tree.return_value = {
                "activities": {"n1": {"name": "回档"}},
            }
            text = failure.get_last_failed_node_logs("root-x", max_chars=400)

        assert "step-28" in text or "step-29" in text
        assert "省略" in text
        assert "step-0" not in text

    def test_folds_consecutive_heartbeat_and_retry_errors(self):
        failure = _failure()
        heartbeats = [{"levelname": "INFO", "message": f"[2026-08-10 14:{i:02d}:00]heartbeat"} for i in range(60)]
        retries = [
            {
                "levelname": "ERROR",
                "message": (
                    f"##[error][2026-08-10 14:25:{i:02d} error][dbactuator-1.1.1.1]: "
                    "NewRedisClient failed :redis new conn fail"
                ),
            }
            for i in range(15)
        ]
        last_failed = SimpleNamespace(
            node_id="n1",
            version_id="v1",
            status="FAILED",
            started_at=timezone.now(),
            updated_at=timezone.now(),
        )
        with patch(
            f"{FAILURE_MODULE}._pick_last_abnormal_flow_node",
            return_value=(last_failed, "failed_or_revoked"),
        ), patch("backend.flow.engine.bamboo.engine.BambooEngine") as mock_engine_cls, patch(
            f"{FAILURE_MODULE}._fetch_node_logs_capped",
            return_value=heartbeats + retries,
        ):
            mock_engine_cls.return_value.get_pipeline_tree.return_value = {
                "activities": {"n1": {"name": "回档"}},
            }
            text = failure.get_last_failed_node_logs("root-x", max_chars=2000)

        assert text.count("heartbeat") == 1
        assert "连续重复 59 次" in text
        assert text.count("NewRedisClient failed") == 1
        assert "连续重复 14 次" in text
        assert "末次" in text

    def test_non_consecutive_duplicates_not_folded(self):
        failure = _failure()
        lines = [
            {"levelname": "ERROR", "message": "same-err"},
            {"levelname": "INFO", "message": "middle"},
            {"levelname": "ERROR", "message": "same-err"},
        ]
        assert failure._fold_consecutive_duplicate_lines([failure._format_log_line(x) for x in lines]) == [
            "[ERROR] same-err",
            "[INFO] middle",
            "[ERROR] same-err",
        ]

    def test_oversized_line_keeps_tail(self):
        failure = _failure()
        assert failure._tail_truncate_line("abcdef", 4) == "...f"
        assert failure._tail_truncate_line("abcdef", 0) == ""
        truncated = failure._tail_truncate_line("prefix-" + ("x" * 100) + "-EXCEPTION", 30)
        assert truncated.startswith("...")
        assert truncated.endswith("EXCEPTION")
        leveled = failure._tail_truncate_line("[ERROR] " + ("x" * 100) + "-boom", 25)
        assert leveled.startswith("[ERROR]")
        assert "boom" in leveled

    def test_tight_budget_keeps_error_over_trailing_context(self):
        """Trailing INFO context of the error window must not starve the error line."""
        failure = _failure()
        lines = [
            "[ERROR] " + ("x" * 100) + "-boom",
            "[INFO] ctx-after-1",
            "[INFO] ctx-after-2",
        ]
        selected = failure._select_log_lines_for_budget(lines, 40)
        text = "\n".join(selected)
        assert "[ERROR]" in text
        assert "boom" in text
        assert len(text) <= 40

    def test_es_query_uses_capped_size_and_desc_sort(self):
        failure = _failure()
        with patch(f"{FAILURE_MODULE}.BKLogApi", create=True), patch(
            "backend.components.BKLogApi.esquery_search"
        ) as mock_search:
            mock_search.return_value = {"hits": {"hits": []}}
            failure._esquery_search_capped(
                indices="idx",
                query_string="q",
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-02 00:00:00",
                size=123,
            )
        payload = mock_search.call_args.args[0]
        assert payload["size"] == 123
        assert payload["sort_list"] == failure._BKLOG_SORT_DESC

    def test_head_tail_truncate_helper(self):
        failure = _failure()
        text = "H" * 100 + "M" * 500 + "T" * 100
        out = failure._head_tail_truncate(text, max_chars=250, head_chars=80)
        assert out.startswith("H" * 80)
        assert "中间截断" in out
        assert out.endswith("T" * 100) or "T" * 50 in out


# ---------------------------------------------------------------------------
# Weekly WeCom formatting / skip
# ---------------------------------------------------------------------------


class TestWeeklyWecom:
    def test_format_headline_includes_share_url(self):
        weekly = _weekly()
        stats = {
            "total": 10,
            "done": 7,
            "failed": 2,
            "skipped": 1,
            "success_rate_pct": 70.0,
            "missing_analysis_count": 0,
            "failure_category_distribution": {"构造流程失败": 2},
        }
        delta = {"total": 1, "failed": -1, "success_rate_pct": 5.0}
        text = weekly.format_wecom_headline(stats, delta, "https://example/ai-chat/share/abc/", "win")
        assert "https://example/ai-chat/share/abc/" in text
        assert "70.0" in text

    @patch(f"{WEEKLY_MODULE}.load_chat_ids_by_priority", return_value=[])
    @patch(f"{WEEKLY_MODULE}.CmsiHandler")
    def test_send_skipped_when_no_chat_ids(self, mock_handler, _mock_ids):
        weekly = _weekly()
        assert weekly.send_weekly_summary_to_qywx("hello") is False
        mock_handler.assert_not_called()

    @patch(f"{WEEKLY_MODULE}.CmsiHandler")
    @patch(f"{WEEKLY_MODULE}.load_chat_ids_by_priority", return_value=["cid-1"])
    def test_send_uses_cmsi_wecom_robot(self, _mock_ids, mock_handler):
        weekly = _weekly()
        assert weekly.send_weekly_summary_to_qywx("hello\nworld") is True
        mock_handler.return_value.send_wecom_robot.assert_called()


class TestRunWeeklySummary(TestCase):
    databases = {"default", "report_db"}

    def _create(self, **overrides):
        kwargs = dict(
            bk_biz_id=100,
            bk_cloud_id=0,
            cluster_id=10001,
            cluster_domain="cache-a.dba.db",
            cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
            instance_ip="1.1.1.1",
            instance_port=30000,
            redis_version="6.2.7",
            task_stage=TaskStage.ROLLBACK_FAILED,
            creator="system",
            updater="system",
        )
        kwargs.update(overrides)
        return Report.objects.create(**kwargs)

    def tearDown(self):
        Report.objects.all().delete()
        from backend.db_report.models.ai_analysis_report import AiAnalysisReport

        AiAnalysisReport.objects.filter(ai_agent="ai-redis-exana").delete()

    @patch(f"{WEEKLY_MODULE}.send_weekly_summary_to_qywx", return_value=True)
    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    @patch(f"{WEEKLY_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_run_persists_ai_report(self, _mock_enabled, mock_ask, _mock_send):
        weekly = _weekly()
        mock_ask.return_value = "# 周报\n\n概览：一切正常"
        with patch.object(weekly.env, "BK_SAAS_HOST", "https://dbm.example.com"):
            report_id = weekly.run_weekly_ai_summary(now=_aware(2026, 8, 7, 19, 0))

        assert report_id
        from backend.db_report.models.ai_analysis_report import AiAnalysisReport

        saved = AiAnalysisReport.objects.get(id=report_id)
        assert saved.ai_agent == "ai-redis-exana"
        assert "周报" in saved.get_content()
        cost_match = re.search(r"AI耗时:(\d+\.\d)s", saved.summary)
        assert cost_match, saved.summary
        assert float(cost_match.group(1)) >= 0.0

    @patch(f"{WEEKLY_MODULE}.send_weekly_summary_to_qywx", return_value=True)
    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    @patch(f"{WEEKLY_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_run_fallback_omits_ai_cost(self, _mock_enabled, mock_ask, _mock_send):
        weekly = _weekly()
        mock_ask.side_effect = Exception("boom")
        with patch.object(weekly.env, "BK_SAAS_HOST", "https://dbm.example.com"):
            report_id = weekly.run_weekly_ai_summary(now=_aware(2026, 8, 7, 19, 0))

        assert report_id
        from backend.db_report.models.ai_analysis_report import AiAnalysisReport

        saved = AiAnalysisReport.objects.get(id=report_id)
        assert "AI耗时" not in saved.summary
        assert "智能体调用失败" in saved.get_content()

    @patch(f"{WEEKLY_MODULE}.is_exercise_ai_analysis_enabled", return_value=False)
    def test_run_skips_when_ai_disabled(self, _mock_enabled):
        weekly = _weekly()
        assert weekly.run_weekly_ai_summary() is None

    @patch(f"{WEEKLY_MODULE}.send_weekly_summary_to_qywx", return_value=True)
    @patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_command")
    @patch(f"{WEEKLY_MODULE}.is_exercise_ai_analysis_enabled", return_value=True)
    def test_monday_window_excludes_this_sundays_batch(self, _mock_enabled, mock_ask, _mock_send):
        weekly = _weekly()
        mock_ask.return_value = "# 周报"
        # Last Sunday 12:00 batch (week just exercised) -> inside the window.
        last_sunday = self._create(cluster_id=1, cluster_domain="last-sun.dba.db")
        Report.objects.filter(pk=last_sunday.pk).update(create_at=_aware(2026, 8, 2, 12, 0))
        # This Sunday 12:00 batch (upcoming week) -> excluded by the Sunday cutoff.
        this_sunday = self._create(cluster_id=2, cluster_domain="this-sun.dba.db")
        Report.objects.filter(pk=this_sunday.pk).update(create_at=_aware(2026, 8, 9, 12, 0))

        weekly.run_weekly_ai_summary(now=_aware(2026, 8, 10, 10, 0))

        stats = json.loads(mock_ask.call_args.kwargs["command_params"]["stats_json"])
        assert stats["total"] == 1
        assert stats["failed"] == 1
