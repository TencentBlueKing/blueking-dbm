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
# Unit tests for ``agent_checks.base`` (and the ``signals`` sibling module).
#
# Covers:
#   * ``_truncate_agent_response_for_log``
#   * ``BaseRedisAgentCheckTask._resolve_agent_timeouts``
#   * ``signals.agent_check_task_failure_handler`` (Celery task_failure signal)
#   * ``signals.register_agent_check_failure_handlers``
#   * ``_should_skip``
#   * ``execute_agent_check`` outcome branches
#   * ``BaseRedisAgentCheckTask.start`` dispatch counters
#
# All tests are pure-unit: the Cluster / ClusterOperateRecord / AgentHandler /
# cache / celery_task touchpoints are patched so no DB or broker is needed.
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import SoftTimeLimitExceeded


# ---------------------------------------------------------------------------
# _truncate_agent_response_for_log
# ---------------------------------------------------------------------------
class TestTruncateAgentResponseForLog:
    @pytest.mark.parametrize("value", [None, 42, {"a": 1}, ["x"]])
    def test_non_string_uses_repr(self, base, value):
        assert base._truncate_agent_response_for_log(value) == repr(value)

    def test_short_string_returned_as_repr(self, base):
        assert base._truncate_agent_response_for_log("hello") == repr("hello")

    def test_exact_max_chars_not_truncated(self, base):
        s = "a" * base.AGENT_RESPONSE_LOG_MAX_CHARS
        assert base._truncate_agent_response_for_log(s) == repr(s)

    def test_long_string_truncated_with_total_len_marker(self, base):
        s = "a" * (base.AGENT_RESPONSE_LOG_MAX_CHARS + 500)
        out = base._truncate_agent_response_for_log(s)
        assert "truncated" in out
        assert f"total_len={len(s)}" in out


# ---------------------------------------------------------------------------
# _resolve_agent_timeouts
# ---------------------------------------------------------------------------
class TestResolveAgentTimeouts:
    """Invariant validation only; config values must flow through unchanged."""

    def _invoke(self, base, make_config, caplog, **overrides):
        fake_self = MagicMock(config=make_config(**overrides))
        caplog.set_level("WARNING")
        result = base.BaseRedisAgentCheckTask._resolve_agent_timeouts(fake_self)
        return result, caplog.text

    def test_default_config_no_warning(self, base, make_config, caplog):
        (invoke, soft, hard), log = self._invoke(base, make_config, caplog)
        assert (invoke, soft, hard) == (
            base.DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS,
            base.DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS,
            base.DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS,
        )
        assert "timeout config issues" not in log

    def test_invariant_violation_warns(self, base, make_config, caplog):
        _, log = self._invoke(
            base,
            make_config,
            caplog,
            agent_invoke_timeout_seconds=600,
            agent_soft_time_limit_seconds=300,
            agent_hard_time_limit_seconds=400,
        )
        assert "invoke<soft<hard violated" in log

    def test_hard_exceeds_dispatch_interval_warns(self, base, make_config, caplog):
        _, log = self._invoke(
            base,
            make_config,
            caplog,
            agent_hard_time_limit_seconds=base.DISPATCH_INTERVAL_SECONDS + 1,
        )
        assert "exceeds" in log and "DISPATCH_INTERVAL_SECONDS" in log

    def test_non_positive_values_coerced_to_one(self, base, make_config, caplog):
        result, _ = self._invoke(
            base,
            make_config,
            caplog,
            agent_invoke_timeout_seconds=0,
            agent_soft_time_limit_seconds=-10,
            agent_hard_time_limit_seconds=-1,
        )
        assert result == (1, 1, 1)

    def test_valid_config_returned_unchanged(self, base, make_config, caplog):
        result, _ = self._invoke(
            base,
            make_config,
            caplog,
            agent_invoke_timeout_seconds=100,
            agent_soft_time_limit_seconds=200,
            agent_hard_time_limit_seconds=300,
        )
        assert result == (100, 200, 300)


# ---------------------------------------------------------------------------
# signals.agent_check_task_failure_handler
# ---------------------------------------------------------------------------
class TestAgentCheckTaskFailureHandler:
    """Filtering by sender is delegated to celery's signal framework now,
    so the handler itself only needs to classify exceptions and emit a log
    line. The previous prefix-matching / sender-None branches no longer exist.
    """

    @staticmethod
    def _sender():
        s = MagicMock()
        s.name = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.fake_task"
        return s

    @staticmethod
    def _fire(signals, **kwargs):
        signals.agent_check_task_failure_handler(task_id="tid", **kwargs)

    def test_worker_lost_tagged_timeout_hard(self, base, signals, caplog):
        from billiard.exceptions import WorkerLostError

        caplog.set_level("ERROR")
        self._fire(signals, sender=self._sender(), exception=WorkerLostError("killed"))
        assert f"outcome={base.OUTCOME_TIMEOUT_HARD}" in caplog.text

    def test_generic_exception_tagged_error(self, base, signals, caplog):
        caplog.set_level("ERROR")
        self._fire(signals, sender=self._sender(), exception=RuntimeError("boom"))
        assert f"outcome={base.OUTCOME_ERROR}" in caplog.text

    def test_no_exception_still_logs_without_crash(self, signals, caplog):
        caplog.set_level("ERROR")
        self._fire(signals, sender=self._sender(), exception=None)
        assert "exc_type=None" in caplog.text


# ---------------------------------------------------------------------------
# signals.register_agent_check_failure_handlers
# ---------------------------------------------------------------------------
class TestRegisterAgentCheckFailureHandlers:
    def test_connects_handler_to_each_agent_check_task(self, signals):
        with patch.object(signals.task_failure, "connect") as mock_connect:
            signals.register_agent_check_failure_handlers()

        assert mock_connect.call_count == 3
        for call in mock_connect.call_args_list:
            assert call.args[0] is signals.agent_check_task_failure_handler
            assert call.kwargs["sender"] is not None
            assert call.kwargs["dispatch_uid"].startswith("agent_check_task_failure:")

        sender_names = {call.kwargs["sender"].name for call in mock_connect.call_args_list}
        assert len(sender_names) == 3  # three distinct celery task senders

    def test_dispatch_uid_keeps_registration_idempotent(self, signals):
        # Two consecutive registrations must produce the same dispatch_uid set
        # so celery dedupes the receiver instead of double-firing.
        with patch.object(signals.task_failure, "connect") as mock_connect:
            signals.register_agent_check_failure_handlers()
            uids_first = [c.kwargs["dispatch_uid"] for c in mock_connect.call_args_list]

        with patch.object(signals.task_failure, "connect") as mock_connect:
            signals.register_agent_check_failure_handlers()
            uids_second = [c.kwargs["dispatch_uid"] for c in mock_connect.call_args_list]

        assert uids_first == uids_second


# ---------------------------------------------------------------------------
# _should_skip
# ---------------------------------------------------------------------------
class TestShouldSkip:
    _ORM = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base.ClusterOperateRecord"

    @pytest.fixture
    def no_recent_tickets(self):
        with patch(self._ORM) as mod:
            mod.objects.filter.return_value.filter.return_value.exists.return_value = False
            yield

    def test_young_cluster(self, base, make_config, make_cluster):
        skipped, reason = base._should_skip(make_config(lookback_days=30), make_cluster(age_days=3))
        assert skipped and "younger" in reason

    def test_offline_cluster(self, base, make_config, make_cluster, no_recent_tickets):
        skipped, reason = base._should_skip(make_config(), make_cluster(phase="offline"))
        assert skipped and "not online" in reason

    def test_in_ignore_list(self, base, make_config, make_cluster, no_recent_tickets):
        skipped, reason = base._should_skip(
            make_config(ignore_cluster_domains=["r.test.db"]),
            make_cluster(domain="r.test.db"),
        )
        assert skipped and "ignore list" in reason

    def test_busy_with_recent_or_active_ticket(self, base, make_config, make_cluster):
        with patch(self._ORM) as mod:
            mod.objects.filter.return_value.filter.return_value.exists.return_value = True
            skipped, reason = base._should_skip(make_config(), make_cluster())
        assert skipped and "recent or active" in reason

    def test_normal_cluster_not_skipped(self, base, make_config, make_cluster, no_recent_tickets):
        skipped, reason = base._should_skip(make_config(), make_cluster())
        assert (skipped, reason) == (False, "")


# ---------------------------------------------------------------------------
# execute_agent_check outcome branches
# ---------------------------------------------------------------------------
class TestExecuteAgentCheck:
    _CLUSTER = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base.Cluster"
    _HANDLER = "backend.dbm_aiagent.agent.handlers.AgentHandler"

    @pytest.fixture
    def invoke(self, base, make_config, make_cluster):
        """Tiny DSL: ``invoke(...)`` runs ``execute_agent_check`` with all external
        collaborators (Cluster ORM, AgentHandler, _should_skip) patched.
        """

        def _call(
            *,
            cluster="default",
            should_skip=(False, ""),
            agent_return="normal report",
            agent_side_effect=None,
            config=None,
            celery_task=None,
            caplog=None,
        ):
            resolved_cluster = make_cluster() if cluster == "default" else cluster
            if config is None:
                config = make_config()
            with patch(self._CLUSTER) as cluster_cls, patch(self._HANDLER) as handler_cls, patch.object(
                base, "_should_skip", return_value=should_skip
            ):
                cluster_cls.objects.filter.return_value.first.return_value = resolved_cluster
                if agent_side_effect is not None:
                    handler_cls.ask_agent_with_content.side_effect = agent_side_effect
                else:
                    handler_cls.ask_agent_with_content.return_value = agent_return
                if caplog is not None:
                    caplog.set_level("DEBUG")
                base.execute_agent_check(
                    agent_code="ai-x",
                    prompt_template="cluster={cluster_domain}",
                    config=config,
                    cluster_id=getattr(resolved_cluster, "id", 0) or 0,
                    celery_task=celery_task,
                )

        return _call

    def test_success(self, base, invoke, caplog):
        invoke(agent_return="normal report", caplog=caplog)
        assert f"outcome={base.OUTCOME_SUCCESS}" in caplog.text
        assert "normal report" in caplog.text

    def test_cluster_not_found(self, base, invoke, caplog):
        invoke(cluster=None, caplog=caplog)
        assert f"outcome={base.OUTCOME_SKIPPED}" in caplog.text
        assert "cluster not found" in caplog.text

    def test_skipped_carries_reason(self, base, invoke, caplog):
        invoke(should_skip=(True, "cluster younger than 14 days"), caplog=caplog)
        assert f"outcome={base.OUTCOME_SKIPPED}" in caplog.text
        assert "younger" in caplog.text

    def test_soft_timeout(self, base, invoke, caplog):
        invoke(agent_side_effect=SoftTimeLimitExceeded("stl"), caplog=caplog)
        assert f"outcome={base.OUTCOME_TIMEOUT_SOFT}" in caplog.text

    def test_rate_limit_retry_reschedules(self, base, invoke, make_config, celery_task_mock, caplog):
        celery_task_mock.request.retries = 0
        with pytest.raises(celery_task_mock._retry_exc):
            invoke(
                agent_side_effect=Exception("HTTP 429 too many requests"),
                config=make_config(max_rate_limit_retries=3),
                celery_task=celery_task_mock,
                caplog=caplog,
            )
        celery_task_mock.retry.assert_called_once()
        assert f"outcome={base.OUTCOME_RATELIMIT_RETRY}" in caplog.text

    def test_rate_limit_gave_up_after_max_retries(self, base, invoke, make_config, celery_task_mock, caplog):
        celery_task_mock.request.retries = 3
        invoke(
            agent_side_effect=Exception("429 rate limit"),
            config=make_config(max_rate_limit_retries=3),
            celery_task=celery_task_mock,
            caplog=caplog,
        )
        celery_task_mock.retry.assert_not_called()
        assert f"outcome={base.OUTCOME_RATELIMIT_GAVE_UP}" in caplog.text
        assert f"outcome={base.OUTCOME_ERROR}" not in caplog.text  # not double-logged

    def test_generic_error(self, base, invoke, caplog):
        invoke(agent_side_effect=RuntimeError("boom"), caplog=caplog)
        assert f"outcome={base.OUTCOME_ERROR}" in caplog.text


# ---------------------------------------------------------------------------
# BaseRedisAgentCheckTask.extra_skip_check + _apply_extra_skip_check
# ---------------------------------------------------------------------------
class TestApplyExtraSkipCheck:
    """Dispatch-time per-page filtering driven by ``extra_skip_check``."""

    _CLUSTER = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base.Cluster"

    def _make_task_with_override(self, base, hook):
        """Return a task whose ``extra_skip_check`` is the supplied hook.

        Bypasses ``__init__`` so we don't need a populated config; the
        helpers under test only need ``self.extra_skip_check``.
        """
        from backend.db_report.enums.redis_sub_type import RedisCheckSubType
        from backend.dbm_aiagent.agent.constants import DBMAgentCode

        class _Task(base.BaseRedisAgentCheckTask):
            subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
            agent_code = DBMAgentCode.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK
            prompt_template = "x"

            def load_config(self):
                return base.BaseCheckConfig()

            def get_celery_task(self):
                return MagicMock()

            extra_skip_check = hook

        return _Task.__new__(_Task)

    def test_default_hook_returns_no_skip(self, base, fake_task_instance):
        # The base no-op must short-circuit so default-path callers don't
        # accidentally pay for the cluster fetch.
        task = fake_task_instance()
        assert task._has_extra_skip_check() is False
        assert task.extra_skip_check(MagicMock()) == (False, "")

    def test_no_override_short_circuits(self, base, fake_task_instance):
        # When the subclass doesn't override, we must not even hit the ORM.
        task = fake_task_instance()
        with patch(self._CLUSTER) as cluster_cls:
            result = task._apply_extra_skip_check(
                task_name="X",
                page_ids=[1, 2, 3],
                page_busy_ids=set(),
                has_extra_skip=False,
            )
        assert result == set()
        cluster_cls.objects.filter.assert_not_called()

    def test_override_filters_eligible_ids(self, base, caplog):
        # Page has 4 ids; one is busy (skipped before us), two should be
        # filtered by the hook, one survives.
        task = self._make_task_with_override(
            base,
            lambda self, cluster: (cluster.id in {2, 3}, f"policy-skip-{cluster.id}"),
        )
        clusters = [SimpleNamespace(id=i) for i in (1, 2, 3)]  # busy=4 already excluded
        with patch(self._CLUSTER) as cluster_cls:
            cluster_cls.objects.filter.return_value = clusters
            caplog.set_level("INFO")
            skipped = task._apply_extra_skip_check(
                task_name="X",
                page_ids=[1, 2, 3, 4],
                page_busy_ids={4},
                has_extra_skip=True,
            )
        assert skipped == {2, 3}
        assert "policy-skip-2" in caplog.text
        assert "policy-skip-3" in caplog.text

    def test_override_only_fetches_non_busy_ids(self, base):
        # Avoid wasting a Cluster.objects.filter on rows we already know
        # we'll skip via the busy filter.
        task = self._make_task_with_override(base, lambda self, cluster: (False, ""))
        with patch(self._CLUSTER) as cluster_cls:
            cluster_cls.objects.filter.return_value = []
            task._apply_extra_skip_check(
                task_name="X",
                page_ids=[1, 2, 3, 4],
                page_busy_ids={2, 4},
                has_extra_skip=True,
            )
        passed_ids = list(cluster_cls.objects.filter.call_args.kwargs["id__in"])
        assert sorted(passed_ids) == [1, 3]

    def test_override_exception_fails_open(self, base, caplog):
        # Hook misbehavior must never silently suppress the entire fleet --
        # exceptions are logged and the cluster proceeds to dispatch.
        def boom(self, _cluster):
            raise RuntimeError("dbconfig 500")

        task = self._make_task_with_override(base, boom)
        with patch(self._CLUSTER) as cluster_cls:
            cluster_cls.objects.filter.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
            caplog.set_level("WARNING")
            skipped = task._apply_extra_skip_check(
                task_name="X",
                page_ids=[1, 2],
                page_busy_ids=set(),
                has_extra_skip=True,
            )
        assert skipped == set()
        assert "extra_skip_check raised" in caplog.text

    def test_vanished_cluster_is_silently_passed_through(self, base):
        # Cluster row gone between candidate scan and skip-check fetch:
        # don't skip here -- let the worker's "cluster not found" branch
        # log it consistently.
        task = self._make_task_with_override(
            base,
            lambda self, cluster: (True, "should-not-fire"),  # would skip if called
        )
        with patch(self._CLUSTER) as cluster_cls:
            cluster_cls.objects.filter.return_value = []  # nothing returned for [1, 2]
            skipped = task._apply_extra_skip_check(
                task_name="X",
                page_ids=[1, 2],
                page_busy_ids=set(),
                has_extra_skip=True,
            )
        assert skipped == set()


# ---------------------------------------------------------------------------
# BaseRedisAgentCheckTask.start
# ---------------------------------------------------------------------------
class TestStartDispatch:
    _CACHE = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base.cache"

    def _prepare(self, fake_task_instance, *, cluster_ids=(1, 2, 3), apply_async=None, **config_overrides):
        task = fake_task_instance(**config_overrides)
        task.get_clusters_to_check = lambda: list(cluster_ids)
        celery_task = MagicMock()
        if apply_async is not None:
            celery_task.apply_async.side_effect = apply_async
        task.get_celery_task = lambda: celery_task
        return task, celery_task

    def test_disabled_returns_zero(self, fake_task_instance):
        task = fake_task_instance()
        task.config.enabled = False
        assert task.start() == 0

    def test_no_candidates_returns_zero(self, fake_task_instance):
        task = fake_task_instance()
        task.get_clusters_to_check = lambda: []
        assert task.start() == 0

    def test_all_dispatched_ok(self, fake_task_instance, caplog):
        task, celery_task = self._prepare(fake_task_instance, cluster_ids=[10, 11])
        caplog.set_level("INFO")
        assert task.start() == 2
        assert celery_task.apply_async.call_count == 2
        assert "ok=2 failed=0" in caplog.text

    def test_apply_async_kwargs_include_time_limits(self, base, fake_task_instance):
        task, celery_task = self._prepare(fake_task_instance, cluster_ids=[1])
        task.start()
        _args, kwargs = celery_task.apply_async.call_args
        assert kwargs["soft_time_limit"] == base.DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS
        assert kwargs["time_limit"] == base.DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS
        assert kwargs["expires"] == base.DISPATCH_INTERVAL_SECONDS

    def test_dispatch_failure_counted_separately(self, base, fake_task_instance, caplog):
        calls = {"n": 0}

        def flaky(*_a, **_kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("broker down")

        task, celery_task = self._prepare(fake_task_instance, cluster_ids=[1, 2], apply_async=flaky)
        caplog.set_level("INFO")
        assert task.start() == 1
        assert "ok=1 failed=1" in caplog.text
        assert f"outcome={base.OUTCOME_DISPATCH_FAILED}" in caplog.text

    def test_dedupe_lock_skips_dispatch(self, base, fake_task_instance, caplog):
        task, celery_task = self._prepare(fake_task_instance, cluster_ids=[1, 2], enable_inflight_dedupe=True)
        with patch(self._CACHE) as cache_mod:
            cache_mod.add.side_effect = [True, False]  # second cluster already in-flight
            caplog.set_level("DEBUG")
            assert task.start() == 1
        assert celery_task.apply_async.call_count == 1
        assert "dedupe_skipped=1" in caplog.text
        assert f"outcome={base.OUTCOME_DISPATCH_DEDUP_SKIPPED}" in caplog.text
