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

from unittest.mock import MagicMock, patch

import pytest


class TestTruncateAgentResponseForLog:
    @pytest.mark.parametrize("value", [None, 42, {"a": 1}, ["x"]])
    def test_non_string_uses_repr(self, ai_tasks, value):
        from backend.dbm_aiagent.tasks.invoker import _truncate_agent_response_for_log

        assert _truncate_agent_response_for_log(value) == repr(value)

    def test_short_string_returned_as_repr(self, ai_tasks):
        from backend.dbm_aiagent.tasks.invoker import _truncate_agent_response_for_log

        assert _truncate_agent_response_for_log("hello") == repr("hello")

    def test_exact_max_chars_not_truncated(self, ai_tasks):
        from backend.dbm_aiagent.tasks.invoker import AGENT_RESPONSE_LOG_MAX_CHARS, _truncate_agent_response_for_log

        s = "a" * AGENT_RESPONSE_LOG_MAX_CHARS
        assert _truncate_agent_response_for_log(s) == repr(s)

    def test_long_string_truncated_with_total_len_marker(self, ai_tasks):
        from backend.dbm_aiagent.tasks.invoker import AGENT_RESPONSE_LOG_MAX_CHARS, _truncate_agent_response_for_log

        s = "a" * (AGENT_RESPONSE_LOG_MAX_CHARS + 500)
        out = _truncate_agent_response_for_log(s)
        assert "truncated" in out
        assert f"total_len={len(s)}" in out


class TestAgentCheckTaskFailureHandler:
    @staticmethod
    def _sender():
        s = MagicMock()
        s.name = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.fake_task"
        return s

    @staticmethod
    def _fire(**kwargs):
        from backend.db_periodic_task.dispatch.signals import dispatch_failure_handler

        dispatch_failure_handler(task_id="tid", **kwargs)

    def test_worker_lost_tagged_error(self, ai_tasks, caplog):
        from billiard.exceptions import WorkerLostError

        caplog.set_level("ERROR")
        self._fire(sender=self._sender(), exception=WorkerLostError("killed"))
        assert f"outcome={ai_tasks.DispatchOutcomeType.ERROR}" in caplog.text
        assert "worker_lost=True" in caplog.text

    def test_worker_lost_drops_reserved_when_job_exists(self, ai_tasks):
        from billiard.exceptions import WorkerLostError

        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        job = MagicMock()
        job.namespace = "ai"
        job.task_key = "dummy.smoke"
        job.work_item_id = "item-1"
        queue_cls = MagicMock()
        with (
            patch.object(DispatchTask, "fetch_job", return_value=job) as fetch_job,
            patch.object(DispatchQueue, "queue_for_namespace", return_value=queue_cls),
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as lifecycle_finalize,
            patch("backend.db_periodic_task.dispatch.metrics.DispatchMetrics.record_queue_event") as record_queue,
        ):
            self._fire(
                sender=self._sender(),
                exception=WorkerLostError("killed"),
                args=["dummy.smoke:item-1"],
            )

        fetch_job.assert_called_once_with("dummy.smoke:item-1")
        record_queue.assert_called_once_with("ai", "celery_failure")
        queue_cls.record_outcome.assert_called_once_with("dummy.smoke", DispatchOutcomeType.ERROR)
        lifecycle_finalize.assert_called_once_with(
            queue_cls=queue_cls,
            job_id="dummy.smoke:item-1",
            task_key="dummy.smoke",
            work_item_id="item-1",
        )

    def test_worker_lost_finalizes_in_job_namespace_when_queue_unregistered(self):
        from billiard.exceptions import WorkerLostError

        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.queue import DISPATCH_QUEUE_REGISTRY, DispatchQueue

        job = MagicMock()
        job.namespace = "gone"
        job.task_key = "gone.task"
        job.work_item_id = "item-1"
        with (
            patch.object(DispatchTask, "fetch_job", return_value=job),
            patch.object(DispatchQueue, "queue_for_namespace", return_value=None),
            patch.object(DispatchQueue, "record_outcome") as record_outcome,
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as lifecycle_finalize,
            patch("backend.db_periodic_task.dispatch.metrics.DispatchMetrics.record_queue_event"),
        ):
            self._fire(
                sender=self._sender(),
                exception=WorkerLostError("killed"),
                args=["gone.task:item-1"],
            )

        record_outcome.assert_called_once()
        lifecycle_finalize.assert_called_once()
        queue_cls = lifecycle_finalize.call_args.kwargs["queue_cls"]
        assert queue_cls is not DispatchQueue
        assert queue_cls.namespace == "gone"
        assert queue_cls.reserved_key() == "dispatch:gone:reserved"
        assert DISPATCH_QUEUE_REGISTRY.get("gone") is None

    def test_worker_lost_ignores_missing_job(self):
        from billiard.exceptions import WorkerLostError

        from backend.db_periodic_task.dispatch.base import DispatchTask

        with (
            patch.object(DispatchTask, "fetch_job", return_value=None) as fetch_job,
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as finalize_job,
        ):
            self._fire(
                sender=self._sender(),
                exception=WorkerLostError("killed"),
                args=["gone:job"],
            )

        fetch_job.assert_called_once_with("gone:job")
        finalize_job.assert_not_called()

    def test_hard_time_limit_drops_reserved_when_job_exists(self):
        from celery.exceptions import TimeLimitExceeded

        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        job = MagicMock()
        job.namespace = "ai"
        job.task_key = "dummy.smoke"
        job.work_item_id = "item-1"
        queue_cls = MagicMock()
        with (
            patch.object(DispatchTask, "fetch_job", return_value=job),
            patch.object(DispatchQueue, "queue_for_namespace", return_value=queue_cls),
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as lifecycle_finalize,
            patch("backend.db_periodic_task.dispatch.metrics.DispatchMetrics.record_queue_event"),
        ):
            self._fire(
                sender=self._sender(),
                exception=TimeLimitExceeded("hard limit hit"),
                args=["dummy.smoke:item-1"],
            )

        # The threads pool raises TimeLimitExceeded when the worker's hard
        # --time-limit kills a task: reclaim the reserved slot immediately.
        queue_cls.record_outcome.assert_called_once_with("dummy.smoke", DispatchOutcomeType.ERROR)
        lifecycle_finalize.assert_called_once_with(
            queue_cls=queue_cls,
            job_id="dummy.smoke:item-1",
            task_key="dummy.smoke",
            work_item_id="item-1",
        )

    def test_soft_time_limit_does_not_drop_reserved(self):
        from celery.exceptions import SoftTimeLimitExceeded

        from backend.db_periodic_task.dispatch.base import DispatchTask

        with (
            patch.object(DispatchTask, "fetch_job") as fetch_job,
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as finalize_job,
        ):
            self._fire(
                sender=self._sender(),
                exception=SoftTimeLimitExceeded("soft limit, keep running"),
                args=["x:y"],
            )

        # A soft limit is advisory only: the task is still executing, so the
        # reserved slot must stay reserved.
        fetch_job.assert_not_called()
        finalize_job.assert_not_called()

    def test_generic_exception_does_not_drop_reserved(self, ai_tasks, caplog):
        from backend.db_periodic_task.dispatch.base import DispatchTask

        caplog.set_level("ERROR")
        with (
            patch.object(DispatchTask, "fetch_job") as fetch_job,
            patch("backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job") as finalize_job,
        ):
            self._fire(sender=self._sender(), exception=RuntimeError("boom"), args=["x:y"])
        assert f"outcome={ai_tasks.DispatchOutcomeType.ERROR}" in caplog.text
        fetch_job.assert_not_called()
        finalize_job.assert_not_called()

    def test_no_exception_still_logs_without_crash(self, caplog):
        caplog.set_level("ERROR")
        self._fire(sender=self._sender(), exception=None)
        assert "exc_type=None" in caplog.text


class TestRegisterAgentCheckFailureHandlers:
    def test_connects_handler_to_generic_worker_task(self):
        from celery.signals import task_failure

        from backend.db_periodic_task.dispatch.registry import dispatch_execute_job, register_failure_handlers
        from backend.db_periodic_task.dispatch.signals import dispatch_failure_handler

        with patch.object(task_failure, "connect") as mock_connect:
            register_failure_handlers()

        assert mock_connect.call_count >= 1
        senders = [call.kwargs["sender"] for call in mock_connect.call_args_list]
        assert dispatch_execute_job in senders
        for call in mock_connect.call_args_list:
            assert call.args[0] is dispatch_failure_handler
            assert call.kwargs["dispatch_uid"].startswith("dispatch_failure:")

    def test_dispatch_uid_keeps_registration_idempotent(self):
        from celery.signals import task_failure

        from backend.db_periodic_task.dispatch.registry import register_failure_handlers

        with patch.object(task_failure, "connect") as mock_connect:
            register_failure_handlers()
            uids_first = [c.kwargs["dispatch_uid"] for c in mock_connect.call_args_list]

        with patch.object(task_failure, "connect") as mock_connect:
            register_failure_handlers()
            uids_second = [c.kwargs["dispatch_uid"] for c in mock_connect.call_args_list]

        assert uids_first == uids_second


class TestOnBeforeExecute:
    _ORM = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter.ClusterOperateRecord"

    @pytest.fixture
    def no_recent_tickets(self):
        with patch(self._ORM) as mod:
            mod.objects.filter.return_value.filter.return_value.exists.return_value = False
            yield

    def test_offline_cluster(self, fake_task_instance, make_cluster, no_recent_tickets):
        task = fake_task_instance()
        reason = task.on_before_execute(
            {"cluster_id": make_cluster(phase="offline").id, "cluster": make_cluster(phase="offline")}
        )
        assert reason and "not online" in reason

    def test_busy_with_recent_or_active_ticket(self, fake_task_instance, make_cluster):
        task = fake_task_instance()
        with patch(self._ORM) as mod:
            mod.objects.filter.return_value.filter.return_value.exists.return_value = True
            reason = task.on_before_execute({"cluster_id": make_cluster().id, "cluster": make_cluster()})
        assert reason and "recent or active" in reason

    def test_normal_cluster_not_skipped(self, fake_task_instance, make_cluster, no_recent_tickets):
        task = fake_task_instance()
        assert task.on_before_execute({"cluster_id": make_cluster().id, "cluster": make_cluster()}) is None


class TestAgentInvokerOutcomes:
    _HANDLER = "backend.dbm_aiagent.agent.handlers.AgentHandler"

    @pytest.fixture
    def invoke(self, make_config, make_cluster):
        from backend.dbm_aiagent.tasks.invoker import AgentInvoker, AgentRequest

        def _call(
            *,
            cluster="default",
            agent_return="normal report",
            agent_side_effect=None,
            config=None,
            caplog=None,
        ):
            resolved_cluster = make_cluster() if cluster == "default" else cluster
            if config is None:
                config = make_config()
            with patch(self._HANDLER) as handler_cls:
                if agent_side_effect is not None:
                    handler_cls.ask_agent_with_content.side_effect = agent_side_effect
                else:
                    handler_cls.ask_agent_with_content.return_value = agent_return
                if caplog is not None:
                    caplog.set_level("DEBUG")
                return AgentInvoker.invoke(
                    task_key="test.task",
                    agent_code="ai-x",
                    request=AgentRequest(content=f"cluster={resolved_cluster.immute_domain}"),
                    execution_timeout_seconds=config.execution_timeout_seconds,
                    requeue_cooldown_seconds=config.requeue_cooldown_seconds,
                    work_item_ref=f"cluster:{resolved_cluster.id}",
                )

        return _call

    def test_success(self, ai_tasks, invoke, caplog):
        outcome = invoke(agent_return="normal report", caplog=caplog)
        assert outcome.outcome == ai_tasks.DispatchOutcomeType.SUCCESS

    def test_api_timeout(self, ai_tasks, invoke, caplog):
        outcome = invoke(agent_side_effect=TimeoutError("api timeout"), caplog=caplog)
        assert outcome.outcome == ai_tasks.DispatchOutcomeType.TIMEOUT

    def test_rate_limit_signals_requeue(self, ai_tasks, invoke, make_config, caplog):
        class _RateLimited(Exception):
            status_code = 429

        outcome = invoke(
            agent_side_effect=_RateLimited("too many requests"),
            config=make_config(max_requeue_attempts=3),
            caplog=caplog,
        )
        assert outcome.should_requeue is True

    def test_generic_error(self, ai_tasks, invoke, caplog):
        outcome = invoke(agent_side_effect=RuntimeError("boom"), caplog=caplog)
        assert outcome.outcome == ai_tasks.DispatchOutcomeType.ERROR


class TestSubmitDispatch:
    _LIMITER = "backend.db_periodic_task.dispatch.admission.QueueAdmission.enqueue_jobs"

    def _prepare(self, fake_task_instance, *, cluster_ids=(1, 2, 3), **config_overrides):
        task = fake_task_instance(**config_overrides)
        clusters = [{"cluster_id": cid, "cluster_domain": f"cluster-{cid}.db"} for cid in cluster_ids]
        return task, clusters

    def test_disabled_config_still_submits_when_called_directly(self, fake_task_instance):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        task = fake_task_instance()
        task.config.enabled = False
        with patch(self._LIMITER, return_value=[EnqueueStatus.ACCEPTED]) as mock_enqueue:
            outcomes = task.submit([{"cluster_id": 1, "cluster_domain": "cluster-1.db"}])
        assert mock_enqueue.call_count == 1
        assert len(outcomes) == 1

    def test_all_enqueued_ok(self, fake_task_instance, caplog):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        task, clusters = self._prepare(fake_task_instance, cluster_ids=[10, 11])
        with patch(self._LIMITER, return_value=[EnqueueStatus.ACCEPTED, EnqueueStatus.ACCEPTED]) as mock_enqueue:
            caplog.set_level("INFO")
            outcomes = task.submit(clusters)
        assert mock_enqueue.call_count == 1
        assert len(outcomes) == 2

    def test_enqueue_failure_returns_capacity_rejected_outcome(self, ai_tasks, fake_task_instance):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        task, clusters = self._prepare(fake_task_instance, cluster_ids=[1, 2])
        with patch(
            self._LIMITER,
            return_value=[EnqueueStatus.ACCEPTED, EnqueueStatus.CAPACITY_REJECTED],
        ):
            outcomes = task.submit(clusters)
        assert outcomes[0].outcome == ai_tasks.DispatchOutcomeType.ENQUEUED
        assert outcomes[1].outcome == ai_tasks.DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED

    def test_single_item_submit(self, fake_task_instance):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        task = fake_task_instance()
        with patch(self._LIMITER, return_value=[EnqueueStatus.ACCEPTED]):
            outcomes = task.submit({"cluster_id": 1, "cluster_domain": "cluster-1.db"})
        assert len(outcomes) == 1
