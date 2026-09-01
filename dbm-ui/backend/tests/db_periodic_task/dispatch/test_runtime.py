import importlib
import json
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, call, patch

import pytest

from backend.db_periodic_task.dispatch.admission import EnqueueStatus, QueueAdmission
from backend.db_periodic_task.dispatch.config import (
    DISPATCH_LUA_BATCH_SIZE,
    TASK_COUNTS_REBUILD_FORCE_SECONDS,
    TASK_COUNTS_REBUILD_PERIOD_SECONDS,
    TASK_COUNTS_REBUILD_REQUEST_TTL_SECONDS,
    TASK_COUNTS_REBUILD_RETRY_SECONDS,
    DispatchPumpConfig,
    DispatchQueueConfig,
    DispatchTaskConfig,
)
from backend.db_periodic_task.dispatch.job import DispatchJob, resolve_task_key_from_job_id
from backend.db_periodic_task.dispatch.lifecycle import QueueLifecycle, RequeueResult
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.queue import (
    DISPATCH_QUEUE_REGISTRY,
    TASK_COUNTS_TTL_SECONDS,
    DispatchQueue,
    DispatchQueueError,
)
from backend.db_periodic_task.dispatch.reaper import REAP_CURSOR_TTL_SECONDS, OrphanReaper
from backend.db_periodic_task.dispatch.reservation import (
    BACKPRESSURE_STATUSES,
    RESERVE_JOB_LUA,
    QueueReservation,
    ReservationStatus,
)
from backend.db_periodic_task.dispatch.task_counts import TaskCounts


@pytest.fixture(scope="module")
def pump_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.dispatch.pump")


@pytest.fixture(scope="module")
def maintenance_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.dispatch.maintenance")


class TestDispatchConfigModels:
    def test_queue_defaults_are_explicit_capacity_ceilings(self):
        assert DispatchQueueConfig().max_admitted_jobs == 2000
        assert DispatchQueueConfig().max_reserved == 10

    def test_pump_timing_is_derived_from_cadence(self):
        config = DispatchPumpConfig()
        assert config.deadline_seconds == 8.0
        assert config.lock_ttl_seconds == 11
        assert TASK_COUNTS_REBUILD_PERIOD_SECONDS == 10 * 60
        assert TASK_COUNTS_REBUILD_FORCE_SECONDS == 24 * 3600

    @pytest.mark.django_db
    def test_task_config_is_stored_in_dedicated_models(self):
        from backend.db_periodic_task.models import DispatchQueueSettings, DispatchTaskSettings

        @dataclass
        class ExampleConfig(DispatchTaskConfig):
            queue_namespace = "test-runtime"
            task_key = "test-runtime.task"
            enabled: bool = True

        with patch("backend.db_periodic_task.dispatch.config_cache.DispatchSettingsCache.invalidate_queue"), patch(
            "backend.db_periodic_task.dispatch.config_cache.DispatchSettingsCache.invalidate_task"
        ):
            ExampleConfig(requeue_cooldown_seconds=7).save_to_db(user="tester")

        queue = DispatchQueueSettings.objects.get(namespace="test-runtime")
        task = DispatchTaskSettings.objects.get(task_key="test-runtime.task")
        assert task.queue == queue
        assert task.config["requeue_cooldown_seconds"] == 7
        assert task.creator == "tester"

    @pytest.mark.django_db(transaction=True)
    def test_settings_invalidate_cache_after_commit(self):
        """Admin/atomic saves must not invalidate before the DB write is visible."""
        from django.db import transaction

        from backend.db_periodic_task.models import DispatchQueueSettings, DispatchTaskSettings

        queue = DispatchQueueSettings.objects.create(
            namespace="test-on-commit-q",
            config={"max_reserved": 3, "max_admitted_jobs": 10},
            creator="tester",
            updater="tester",
        )
        task = DispatchTaskSettings.objects.create(
            queue=queue,
            task_key="test-on-commit.task",
            config={"enabled": True},
            creator="tester",
            updater="tester",
        )

        with patch(
            "backend.db_periodic_task.dispatch.config_cache.DispatchSettingsCache.invalidate_queue"
        ) as inv_q, patch(
            "backend.db_periodic_task.dispatch.config_cache.DispatchSettingsCache.invalidate_task"
        ) as inv_t:
            with transaction.atomic():
                queue.config = {"max_reserved": 9, "max_admitted_jobs": 10}
                queue.save()
                task.config = {"enabled": False}
                task.save()
                inv_q.assert_not_called()
                inv_t.assert_not_called()

            inv_q.assert_called_once_with("test-on-commit-q")
            inv_t.assert_called_once_with("test-on-commit.task")

    def test_job_config_resolution_handles_live_loader_failure(self):
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

        config_cls = MagicMock()
        config_cls.from_db.side_effect = RuntimeError("cache and DB unavailable")
        task_cls = SimpleNamespace(config_cls=config_cls)
        job = DispatchJob(
            job_id="test-runtime.task:item",
            task_key="test-runtime.task",
            namespace="default",
            work_item_id="item",
        )

        with patch.dict(DISPATCH_REGISTRY, {job.task_key: task_cls}):
            assert DispatchQueue.resolve_stored_task_config(job) is None

        config_cls.from_db.assert_called_once_with()

    def test_job_config_resolution_keeps_default_loader_result(self):
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

        default_config = DispatchTaskConfig()
        config_cls = MagicMock()
        config_cls.from_db.return_value = default_config
        task_cls = SimpleNamespace(config_cls=config_cls)
        job = DispatchJob(
            job_id="test-runtime.task:item",
            task_key="test-runtime.task",
            namespace="default",
            work_item_id="item",
        )

        with patch.dict(DISPATCH_REGISTRY, {job.task_key: task_cls}):
            assert DispatchQueue.resolve_stored_task_config(job) is default_config


class TestStatusEnums:
    def test_no_status_is_zero_so_truthiness_cannot_split_rejections(self):
        """``if status:`` used to be true for every rejection except the one
        that happened to be 0, silently treating it as a different class."""
        assert all(status != 0 for status in EnqueueStatus)
        assert all(status != 0 for status in ReservationStatus)
        assert all(status != 0 for status in RequeueResult)

    def test_dead_eval_is_not_reported_as_capacity_backpressure(self):
        job = TestPumpQueue._job()
        with patch.object(QueueReservation, "_reserve_script", MagicMock(side_effect=RuntimeError("redis down"))):
            statuses = QueueReservation.reserve_jobs(
                [job],
                DispatchQueueConfig(),
                queue_cls=DispatchQueue,
                reserved_record_ttls=[120],
                tick_id=123,
                tick_budget=50,
            )

        assert statuses == [ReservationStatus.UNAVAILABLE]
        assert ReservationStatus.UNAVAILABLE not in BACKPRESSURE_STATUSES


class TestAtomicReservation:
    def test_reservation_chunk_size_keeps_lua_windows_small(self):
        assert DISPATCH_LUA_BATCH_SIZE == 25
        assert "task_counts" in RESERVE_JOB_LUA
        assert "pending:" in RESERVE_JOB_LUA

    def test_reservation_batches_atomic_reserved_snapshot(self):
        script = MagicMock(return_value=[ReservationStatus.RESERVED])
        config = DispatchQueueConfig()
        job = TestPumpQueue._job()
        with patch.object(QueueReservation, "_reserve_script", script):
            statuses = QueueReservation.reserve_jobs(
                [job],
                config,
                queue_cls=DispatchQueue,
                reserved_record_ttls=[120],
                tick_id=123,
                tick_budget=50,
            )

        assert statuses == [ReservationStatus.RESERVED]
        script.assert_called_once()
        assert len(script.call_args.kwargs["keys"]) == 6
        assert script.call_args.kwargs["keys"][2] == "dispatch:default:tick:123"
        assert script.call_args.kwargs["keys"][3] == "dispatch:default:task_counts"
        assert script.call_args.kwargs["args"][4] == 1
        snapshot = json.loads(script.call_args.kwargs["args"][7])
        assert snapshot["wait_deadline_at"] == 0.0
        assert script.call_args.kwargs["args"][2] == 50
        assert script.call_args.kwargs["args"][8] == 120
        assert script.call_args.kwargs["args"][9] == "task"

    def test_denied_reservation_returns_before_tick_counter_write(self):
        concurrency_denied = "reserved_count >= max_reserved"
        budget_denied = "used >= tick_budget"
        counter_write = "redis.call('SET', tick_counter"
        promotion = "redis.call('ZREM', pending"
        snapshot = "redis.call('SET', job_record"
        assert RESERVE_JOB_LUA.index(concurrency_denied) < RESERVE_JOB_LUA.index(counter_write)
        assert RESERVE_JOB_LUA.index(budget_denied) < RESERVE_JOB_LUA.index(counter_write)
        assert RESERVE_JOB_LUA.index(budget_denied) < RESERVE_JOB_LUA.index(promotion)
        assert RESERVE_JOB_LUA.index(budget_denied) < RESERVE_JOB_LUA.index(snapshot)

    def test_reservation_rejects_oversized_pipeline_chunk(self):
        jobs = [
            TestPumpQueue._job(job_id=f"task:{index}", work_item_id=str(index))
            for index in range(DISPATCH_LUA_BATCH_SIZE + 1)
        ]
        with pytest.raises(ValueError, match="chunk"):
            QueueReservation.reserve_jobs(
                jobs,
                DispatchQueueConfig(),
                queue_cls=DispatchQueue,
                reserved_record_ttls=[60] * len(jobs),
                tick_id=123,
                tick_budget=100,
            )

    def test_reservation_uses_one_lua_call_for_the_whole_chunk(self):
        jobs = [
            TestPumpQueue._job(job_id=f"task:{index}", work_item_id=str(index))
            for index in range(DISPATCH_LUA_BATCH_SIZE)
        ]
        script = MagicMock(return_value=[ReservationStatus.RESERVED] * len(jobs))
        with patch.object(QueueReservation, "_reserve_script", script):
            statuses = QueueReservation.reserve_jobs(
                jobs,
                DispatchQueueConfig(max_reserved=100),
                queue_cls=DispatchQueue,
                reserved_record_ttls=[60] * len(jobs),
                tick_id=123,
                tick_budget=100,
            )

        assert statuses == [ReservationStatus.RESERVED] * len(jobs)
        script.assert_called_once()
        assert len(script.call_args.kwargs["keys"]) == 4 + 2 * len(jobs)
        assert len(script.call_args.kwargs["args"]) == 6 + 4 * len(jobs)


class TestPumpQueue:
    @staticmethod
    def _job(**overrides):
        values = {
            "job_id": "task:item",
            "task_key": "task",
            "namespace": "test",
            "work_item_id": "item",
            "created_at": time.time(),
            "ready_at": time.time(),
            "wait_deadline_at": time.time() + 60,
        }
        values.update(overrides)
        return DispatchJob(**values)

    @staticmethod
    def _queue(job, *, statuses):
        queue = MagicMock()
        queue.namespace = "test"
        queue.load_config.return_value = DispatchQueueConfig(max_reserved=2)
        queue.reserved_count.return_value = 0
        queue.peek_ready.return_value = [job.job_id]
        queue.get_jobs.return_value = {job.job_id: job}
        queue.resolve_queue_wait_ttl_from_job.return_value = 60
        queue.resolve_reserved_record_ttl_from_job.return_value = 60
        return queue

    @staticmethod
    def _reserve(statuses, pump_module):
        return patch.object(
            pump_module.QueueReservation,
            "reserve_jobs",
            return_value=statuses,
        )

    @staticmethod
    def _requeue(pump_module):
        return patch.object(pump_module.QueueLifecycle, "requeue", return_value=True)

    def test_denied_head_stays_pending_and_stops_queue(self, pump_module):
        job = self._job()
        queue = self._queue(job, statuses=[ReservationStatus.CAPACITY_FULL])

        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=False), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=2,
                congestion_window=2,
                available_slots=2,
                aimd_action="hold",
            ),
        ), self._reserve([ReservationStatus.CAPACITY_FULL], pump_module), self._requeue(pump_module) as requeue, patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ) as apply_async:
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 0

        requeue.assert_not_called()
        apply_async.assert_not_called()

    def test_unavailable_reservation_is_counted_apart_from_backpressure(self, pump_module):
        """A dead EVAL stops the queue like backpressure does, but it needs its
        own counter: capacity clears on its own, a broken queue does not."""
        job = self._job()
        queue = self._queue(job, statuses=[ReservationStatus.UNAVAILABLE])
        stats = pump_module._PumpTickStats()

        with self._reserve([ReservationStatus.UNAVAILABLE], pump_module), patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ) as apply_async:
            pump_module._reserve_and_publish(
                queue,
                [job],
                DispatchQueueConfig(),
                SimpleNamespace(effective_budget=2),
                time.monotonic() + 10,
                123,
                stats,
            )

        assert stats.reserve_unavailable == 1
        assert stats.blocked == 0
        apply_async.assert_not_called()

    def test_publish_failure_returns_reserved_chunk_to_pending(self, pump_module):
        jobs = [self._job(job_id=f"task:{index}", work_item_id=str(index)) for index in range(2)]
        queue = self._queue(jobs[0], statuses=[ReservationStatus.RESERVED] * 2)
        queue.peek_ready.return_value = [job.job_id for job in jobs]
        queue.get_jobs.return_value = {job.job_id: job for job in jobs}

        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=False), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=2,
                congestion_window=2,
                available_slots=2,
                aimd_action="hold",
            ),
        ), self._reserve([ReservationStatus.RESERVED] * 2, pump_module), self._requeue(pump_module) as requeue, patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async",
            side_effect=RuntimeError("broker unavailable"),
        ):
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 0

        assert requeue.call_count == 2
        for job, requeue_call in zip(jobs, requeue.call_args_list):
            assert requeue_call.kwargs["job"] is job
            assert requeue_call.kwargs["ready_at"] == job.ready_at

    def test_pump_resolves_shared_task_config_once(self, pump_module):
        jobs = [self._job(job_id=f"task:{index}", work_item_id=str(index)) for index in range(2)]
        queue = self._queue(jobs[0], statuses=[ReservationStatus.RESERVED] * 2)
        decision = SimpleNamespace(effective_budget=2)
        stats = pump_module._PumpTickStats()

        with self._reserve([ReservationStatus.RESERVED] * 2, pump_module), patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ):
            pump_module._reserve_and_publish(
                queue,
                jobs,
                DispatchQueueConfig(max_reserved=2),
                decision,
                time.monotonic() + 10,
                123,
                stats,
            )

        queue.resolve_reserved_record_ttl_from_job.assert_called_once_with(jobs[0])
        assert stats.published == 2

    def test_expired_candidate_is_discarded_without_reservation(self, pump_module):
        job = self._job(wait_deadline_at=time.time() - 1)
        queue = self._queue(job, statuses=[ReservationStatus.RESERVED])

        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=False), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=2,
                congestion_window=2,
                available_slots=2,
                aimd_action="hold",
            ),
        ), patch.object(pump_module.OrphanReaper, "discard_orphaned_job") as discard, self._reserve(
            [ReservationStatus.RESERVED], pump_module
        ) as reserve:
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 0

        discard.assert_called_once()
        reserve.assert_not_called()

    def test_large_batch_uses_bounded_reservation_chunks(self, pump_module):
        jobs = [self._job(job_id=f"task:{index}", work_item_id=str(index)) for index in range(1000)]
        queue = self._queue(jobs[0], statuses=[])
        queue.load_config.return_value = DispatchQueueConfig(max_reserved=1000)
        queue.peek_ready.return_value = [job.job_id for job in jobs]
        queue.get_jobs.return_value = {job.job_id: job for job in jobs}
        reserve = MagicMock(side_effect=lambda chunk, _config, **_kwargs: [ReservationStatus.RESERVED] * len(chunk))

        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=False), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=1000,
                congestion_window=1000,
                available_slots=1000,
                aimd_action="hold",
            ),
        ), patch.object(pump_module.QueueReservation, "reserve_jobs", reserve), patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ) as apply_async:
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 1000

        assert reserve.call_count == 1000 // DISPATCH_LUA_BATCH_SIZE
        assert all(len(call.args[0]) <= DISPATCH_LUA_BATCH_SIZE for call in reserve.call_args_list)
        assert apply_async.call_count == 1000

    def test_queue_wait_samples_flush_through_metrics_pipeline(self, pump_module):
        jobs = [
            self._job(
                job_id=f"task:{index}",
                work_item_id=str(index),
                created_at=1000.0,
                ready_at=1003.0,
            )
            for index in range(3)
        ]
        queue = self._queue(jobs[0], statuses=[ReservationStatus.RESERVED] * 3)
        queue.peek_ready.return_value = [job.job_id for job in jobs]
        queue.get_jobs.return_value = {job.job_id: job for job in jobs}

        pipeline = MagicMock()
        queue.conn.return_value.pipeline.return_value = pipeline
        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=False), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=3,
                congestion_window=3,
                available_slots=3,
                aimd_action="hold",
            ),
        ), self._reserve([ReservationStatus.RESERVED] * 3, pump_module), patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ), patch(
            "backend.db_periodic_task.dispatch.pump.DispatchMetrics.record_histogram"
        ) as record_histogram, patch(
            "backend.db_periodic_task.dispatch.pump.DispatchMetrics.record_histogram_values"
        ) as record_histogram_values, patch(
            "backend.db_periodic_task.dispatch.pump.DispatchMetrics.record_queue_event"
        ), patch(
            "backend.db_periodic_task.dispatch.pump.time.time", return_value=1005.0
        ):
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 3

        record_histogram_values.assert_called_once()
        assert record_histogram_values.call_args.args[0:2] == ("test", "queue_wait_seconds")
        assert record_histogram_values.call_args.args[2] == [2.0] * len(jobs)
        assert record_histogram_values.call_args.kwargs["client"] is pipeline
        assert all(call.args[1] != "queue_wait_seconds" for call in record_histogram.call_args_list)
        pipeline.execute.assert_called_once()

    @pytest.mark.parametrize(
        "reap_orphans,drifted,expected_reason",
        [
            (0, False, None),  # no evidence -> no out-of-band rebuild request
            (2, False, "orphaned"),
            (0, True, "count_drift"),
        ],
    )
    def test_cleanup_requests_rebuild_only_on_evidence(self, pump_module, reap_orphans, drifted, expected_reason):
        job = self._job()
        queue = self._queue(job, statuses=[ReservationStatus.RESERVED])

        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=True), patch(
            "backend.db_periodic_task.dispatch.pump.PumpController.decide",
            return_value=SimpleNamespace(
                effective_budget=2,
                congestion_window=2,
                available_slots=2,
                aimd_action="hold",
            ),
        ), patch.object(
            pump_module.OrphanReaper, "reap_orphaned_queue_jobs", return_value=reap_orphans
        ) as reap, patch.object(
            pump_module.TaskCounts, "counts_drifted", return_value=drifted
        ) as drifted_check, patch.object(
            pump_module.TaskCounts, "request_rebuild"
        ) as request_rebuild, patch.object(
            pump_module.TaskCounts, "rebuild"
        ) as rebuild, self._reserve(
            [ReservationStatus.RESERVED], pump_module
        ), patch(
            "backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async"
        ):
            assert pump_module._pump_queue(queue, time.monotonic() + 10, 123) == 1

        reap.assert_called_once()
        drifted_check.assert_called_once()
        if expected_reason is None:
            request_rebuild.assert_not_called()
        else:
            request_rebuild.assert_called_once_with(queue, expected_reason)
        rebuild.assert_not_called()

    def test_maybe_cleanup_skips_entirely_past_deadline(self, pump_module):
        queue = MagicMock()
        queue.namespace = "test"
        with patch("backend.db_periodic_task.dispatch.pump.time.monotonic", return_value=100.0), patch(
            "backend.db_periodic_task.dispatch.pump._cleanup_due"
        ) as cleanup_due, patch.object(pump_module.OrphanReaper, "reap_orphaned_queue_jobs") as reap:
            pump_module._maybe_cleanup_queue(queue, deadline_at=50.0)
        cleanup_due.assert_not_called()
        reap.assert_not_called()

    def test_maybe_cleanup_skips_drift_check_when_deadline_after_reap(self, pump_module):
        queue = MagicMock()
        queue.namespace = "test"
        with patch("backend.db_periodic_task.dispatch.pump._cleanup_due", return_value=True), patch(
            "backend.db_periodic_task.dispatch.pump.time.monotonic",
            side_effect=[1.0, 20.0],
        ), patch.object(pump_module.OrphanReaper, "reap_orphaned_queue_jobs", return_value=0) as reap, patch.object(
            pump_module.TaskCounts, "counts_drifted"
        ) as drifted, patch.object(
            pump_module.TaskCounts, "request_rebuild"
        ) as request_rebuild:
            pump_module._maybe_cleanup_queue(queue, deadline_at=10.0)
        reap.assert_called_once()
        drifted.assert_not_called()
        request_rebuild.assert_not_called()


class TestTaskCountsMaintenance:
    def test_requested_namespace_runs_before_daily_and_only_one_attempts(self, maintenance_module):
        requested = MagicMock()
        requested.namespace = "requested"
        daily = MagicMock()
        daily.namespace = "daily"

        with patch.object(DispatchQueue, "registered_queues", return_value=[daily, requested]), patch.object(
            maintenance_module.TaskCounts,
            "rebuild_requested",
            side_effect=lambda queue_cls: queue_cls.namespace == "requested",
        ), patch.object(
            maintenance_module.TaskCounts,
            "hard_rebuild_due",
            side_effect=lambda queue_cls: queue_cls.namespace == "daily",
        ), patch.object(
            maintenance_module,
            "_maintain_queue",
            return_value=True,
        ) as maintain:
            result = maintenance_module.dispatch_task_counts_maintenance.run()

        assert result == {
            "attempted": 1,
            "namespace": "requested",
            "trigger": "requested",
            "success": True,
        }
        maintain.assert_called_once_with(requested, "requested")

    def test_locked_or_backed_off_namespace_does_not_block_next_candidate(self, maintenance_module):
        first = MagicMock()
        first.namespace = "first"
        second = MagicMock()
        second.namespace = "second"

        with patch.object(DispatchQueue, "registered_queues", return_value=[first, second]), patch.object(
            maintenance_module.TaskCounts, "rebuild_requested", return_value=True
        ), patch.object(
            maintenance_module,
            "_maintain_queue",
            side_effect=[None, False],
        ) as maintain:
            result = maintenance_module.dispatch_task_counts_maintenance.run()

        assert result["namespace"] == "second"
        assert result["success"] is False
        assert maintain.call_args_list == [call(first, "requested"), call(second, "requested")]

    def test_successful_maintenance_marks_daily_window(self, maintenance_module):
        queue = MagicMock()
        queue.namespace = "test"
        with patch.object(maintenance_module, "_try_acquire_rebuild_lock", return_value=True), patch.object(
            maintenance_module, "_release_rebuild_lock"
        ) as release, patch.object(
            maintenance_module.TaskCounts, "try_start_rebuild", return_value=True
        ), patch.object(
            maintenance_module.TaskCounts, "rebuild", return_value={"pending:task": 2}
        ) as rebuild, patch.object(
            maintenance_module.TaskCounts, "mark_rebuilt", return_value=True
        ) as mark_rebuilt:
            assert maintenance_module._maintain_queue(queue, "requested") is True

        rebuild.assert_called_once()
        assert "deadline_at" in rebuild.call_args.kwargs
        mark_rebuilt.assert_called_once()
        release.assert_called_once()

    def test_aborted_maintenance_keeps_backoff_and_does_not_mark_success(self, maintenance_module):
        queue = MagicMock()
        queue.namespace = "test"
        with patch.object(maintenance_module, "_try_acquire_rebuild_lock", return_value=True), patch.object(
            maintenance_module, "_release_rebuild_lock"
        ), patch.object(maintenance_module.TaskCounts, "try_start_rebuild", return_value=True), patch.object(
            maintenance_module.TaskCounts, "rebuild", return_value=None
        ), patch.object(
            maintenance_module.TaskCounts, "mark_rebuilt"
        ) as mark_rebuilt:
            assert maintenance_module._maintain_queue(queue, "daily") is False

        mark_rebuilt.assert_not_called()


class TestGlobalPump:
    def test_pumps_every_queue_independently(self, pump_module):
        queues = [SimpleNamespace(namespace=name) for name in ("a", "b", "c")]
        config = DispatchPumpConfig(max_parallel_queues=1)
        started = []

        def pump_one(queue, _deadline_at, _tick_id):
            started.append(queue.namespace)
            return 2

        def redis_set(key, *_args, **_kwargs):
            return True

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        release_script = MagicMock(return_value=1)
        with patch.object(DispatchQueue, "registered_queues", return_value=queues), patch(
            "backend.db_periodic_task.dispatch.pump.DispatchPumpConfig", return_value=config
        ), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ), patch.object(
            pump_module, "_release_lock_script", release_script
        ), patch(
            "backend.db_periodic_task.dispatch.pump._pump_queue", side_effect=pump_one
        ):
            assert pump_module.dispatch_global_pump() == 6

        # Order is rotated per tick (see the rotation tests below), so what
        # matters here is that every queue gets its own pump and its own lock.
        assert sorted(started) == ["a", "b", "c"]
        assert release_script.call_count == 3

    def test_fan_out_is_capped_by_the_deadline_and_reports_starvation(self, pump_module):
        """The per-tick queue ceiling is emergent, and overflow must be visible.

        ``max_parallel_queues`` is thread concurrency, not a queue cap:
        ``submit_next`` simply stops handing out slots once the deadline passed.
        A starved queue never enters ``_pump_queue``, so it cannot record
        ``pump_ticks_skipped`` — ``pump_not_started`` is the only signal that the fleet is
        wider than one tick can service.

        Measured ceilings per Redis RTT live in ``Notes/DispatchQueue/测试报告.md``.
        """
        queues = [SimpleNamespace(namespace=f"ns{index:02d}", ns=lambda: "shard") for index in range(20)]
        config = DispatchPumpConfig(max_parallel_queues=1)
        # One monotonic tick per second against an 8s deadline, so the fleet is
        # cut off well before all 20 queues are submitted.
        clock = iter([0.0] + [float(step) for step in range(1, 400)])
        pumped: list[str] = []

        def pump_one(queue, _deadline_at, _tick_id):
            pumped.append(queue.namespace)
            return 1

        with patch.object(DispatchQueue, "registered_queues", return_value=queues), patch.object(
            pump_module, "DispatchPumpConfig", return_value=config
        ), patch.object(pump_module, "_try_acquire_pump_lock", return_value=True), patch.object(
            pump_module, "_release_pump_lock"
        ), patch.object(
            pump_module.time, "monotonic", side_effect=lambda: next(clock)
        ), patch.object(
            pump_module.routing, "conn_for_namespace", return_value=MagicMock()
        ), patch.object(
            pump_module.DispatchMetrics, "record_queue_event"
        ) as record_counter, patch(
            "backend.db_periodic_task.dispatch.pump._pump_queue", side_effect=pump_one
        ):
            pump_module.dispatch_global_pump()

        assert 0 < len(pumped) < len(queues), "deadline must truncate a fleet it cannot finish"
        starved = {queue.namespace for queue in queues} - set(pumped)
        flagged = {
            call_args.args[0] for call_args in record_counter.call_args_list if call_args.args[1] == "pump_not_started"
        }
        assert flagged == starved

    def test_pump_order_rotates_so_no_queue_starves_forever(self, pump_module):
        """Rotation turns a fixed starved tail into fair degradation.

        ``registered_queues()`` order is stable, so without rotation the same tail would
        be cut off on every tick. Two properties matter: consecutive ticks must
        not merely shift by one (that would take one tick per queue to work
        through a wide fleet), and every queue must be reached within a bounded
        number of ticks.
        """
        queues = [SimpleNamespace(namespace=f"ns{index:03d}") for index in range(100)]
        served_per_tick = 20
        names = [queue.namespace for queue in queues]

        heads = [names.index(pump_module._rotate_for_tick(queues, tick)[0].namespace) for tick in range(5)]
        assert len(set(heads)) == len(heads), "each tick must start somewhere new"
        assert heads[1] - heads[0] not in (1, -1), "rotation must scatter, not step by one"

        covered: set[str] = set()
        for tick in range(30):
            rotated = pump_module._rotate_for_tick(queues, tick)
            covered.update(queue.namespace for queue in rotated[:served_per_tick])
        assert covered == {queue.namespace for queue in queues}

    def test_cleanup_interval_is_jittered_per_namespace(self, pump_module):
        """A cold start writes every cleanup marker in the same tick, so equal
        periods would make the whole fleet reap in lockstep — and a reaping tick
        costs ~21 Redis round trips instead of ~11, halving the fan-out ceiling.
        """
        from backend.db_periodic_task.dispatch.config import PUMP_CLEANUP_INTERVAL_SECONDS, PUMP_CLEANUP_JITTER_RATIO

        intervals = [pump_module._cleanup_interval_for(f"ns{index:03d}") for index in range(200)]
        ceiling = PUMP_CLEANUP_INTERVAL_SECONDS * (1 + PUMP_CLEANUP_JITTER_RATIO)
        assert all(PUMP_CLEANUP_INTERVAL_SECONDS <= value < ceiling for value in intervals)
        # Spread across most of the window, not clustered on a few values.
        assert len(set(intervals)) > PUMP_CLEANUP_INTERVAL_SECONDS * PUMP_CLEANUP_JITTER_RATIO * 0.8
        # Stable per namespace, so a queue keeps its own phase across ticks.
        assert pump_module._cleanup_interval_for("ns001") == pump_module._cleanup_interval_for("ns001")

    def test_rotation_is_stable_within_a_tick(self, pump_module):
        """Every worker pumping the same tick must agree on the order, so the
        per-namespace locks dedupe instead of two workers racing whole fleets."""
        queues = [SimpleNamespace(namespace=f"ns{index:03d}") for index in range(50)]
        first = pump_module._rotate_for_tick(queues, 12345)
        second = pump_module._rotate_for_tick(queues, 12345)
        assert [queue.namespace for queue in first] == [queue.namespace for queue in second]
        # Rotation is a permutation: nothing dropped, nothing duplicated.
        assert sorted(queue.namespace for queue in first) == sorted(queue.namespace for queue in queues)


class TestPumpPause:
    def test_pause_until_resume_occupies_lock(self, pump_module):
        store = {}

        def redis_set(key, value, nx=False, ex=None, **_kwargs):
            if nx and key in store:
                return False
            store[key] = {"value": value, "ex": ex}
            return True

        def redis_get(key):
            item = store.get(key)
            return None if item is None else item["value"]

        def redis_ttl(key):
            item = store.get(key)
            if item is None:
                return -2
            return -1 if item["ex"] is None else int(item["ex"])

        def release_side_effect(keys, args, **kwargs):
            key = keys[0]
            item = store.get(key)
            if item and item["value"] == args[0]:
                store.pop(key)
                return 1
            return 0

        release_script = MagicMock(side_effect=release_side_effect)

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        redis_client.get.side_effect = redis_get
        redis_client.ttl.side_effect = redis_ttl
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ), patch.object(pump_module, "_release_lock_script", release_script):
            info = pump_module.pause_queue_pump("default", seconds=None)
            assert info == {"namespace": "default", "paused": True, "ttl_seconds": None}
            assert pump_module.is_queue_pump_paused("default") is True
            assert pump_module.queue_pump_pause_ttl("default") == -1
            assert store["dispatch:default:pump_lock"]["value"] == pump_module.PUMP_PAUSE_OWNER
            assert store["dispatch:default:pump_lock"]["ex"] is None

            assert pump_module.resume_queue_pump("default") is True
            assert pump_module.is_queue_pump_paused("default") is False
            assert "dispatch:default:pump_lock" not in store

    def test_inspect_pump_lock_distinguishes_pause_and_pump(self, pump_module):
        store = {}

        def redis_get(key):
            item = store.get(key)
            return None if item is None else item["value"]

        def redis_ttl(key):
            item = store.get(key)
            if item is None:
                return -2
            return -1 if item["ex"] is None else int(item["ex"])

        redis_client = MagicMock()
        redis_client.get.side_effect = redis_get
        redis_client.ttl.side_effect = redis_ttl
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ):
            assert pump_module.inspect_queue_pump_lock("default")["state"] == "free"

            store["dispatch:default:pump_lock"] = {"value": pump_module.PUMP_PAUSE_OWNER, "ex": None}
            paused = pump_module.inspect_queue_pump_lock("default")
            assert paused["state"] == "paused"
            assert paused["owner"] == pump_module.PUMP_PAUSE_OWNER
            assert paused["ttl_seconds"] == -1

            store["dispatch:default:pump_lock"] = {"value": "pump:default:abc123", "ex": 11}
            pumping = pump_module.inspect_queue_pump_lock("default")
            assert pumping["state"] == "pumping"
            assert pumping["owner"] == "pump:default:abc123"
            assert pumping["ttl_seconds"] == 11
            assert pump_module.is_queue_pump_paused("default") is False

    def test_timed_pause_sets_ttl(self, pump_module):
        store = {}

        def redis_set(key, value, nx=False, ex=None, **_kwargs):
            store[key] = {"value": value, "ex": ex}
            return True

        def redis_get(key):
            item = store.get(key)
            return None if item is None else item["value"]

        def redis_ttl(key):
            item = store.get(key)
            if item is None:
                return -2
            return -1 if item["ex"] is None else int(item["ex"])

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        redis_client.get.side_effect = redis_get
        redis_client.ttl.side_effect = redis_ttl
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ):
            info = pump_module.pause_queue_pump("default", seconds=90.2)
            assert info["ttl_seconds"] == 91
            assert store["dispatch:default:pump_lock"]["ex"] == 91
            assert pump_module.queue_pump_pause_ttl("default") == 91

    @pytest.mark.parametrize("paused", [False, True])
    def test_global_pump_skips_queue_whose_lock_cannot_be_taken(self, pump_module, paused):
        queues = [SimpleNamespace(namespace=name) for name in ("a", "b")]
        config = DispatchPumpConfig(max_parallel_queues=2)
        started = []

        def pump_one(queue, _deadline_at, _tick_id):
            started.append(queue.namespace)
            return 1

        def redis_set(key, value, nx=False, ex=None, **_kwargs):
            if key == "dispatch:a:pump_lock" and nx:
                return False
            return True

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        with patch.object(DispatchQueue, "registered_queues", return_value=queues), patch(
            "backend.db_periodic_task.dispatch.pump.DispatchPumpConfig", return_value=config
        ), patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=redis_client,), patch(
            "backend.db_periodic_task.dispatch.pump.is_queue_pump_paused",
            return_value=paused,
        ), patch.object(
            pump_module, "_release_lock_script", MagicMock(return_value=1)
        ), patch(
            "backend.db_periodic_task.dispatch.pump._pump_queue", side_effect=pump_one
        ):
            assert pump_module.dispatch_global_pump() == 1

        assert started == ["b"]

    def test_resume_does_not_clear_live_pump_lock(self, pump_module):
        store = {"dispatch:default:pump_lock": {"value": "pump:default:abc", "ex": 11}}

        def release_side_effect(keys, args, **kwargs):
            key = keys[0]
            item = store.get(key)
            if item and item["value"] == args[0]:
                store.pop(key)
                return 1
            return 0

        release_script = MagicMock(side_effect=release_side_effect)
        redis_client = MagicMock()
        redis_client.get.return_value = "pump:default:abc"
        redis_client.set.return_value = True
        with patch.object(pump_module, "_release_lock_script", release_script), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ):
            assert pump_module.resume_queue_pump("default") is False
            assert store["dispatch:default:pump_lock"]["value"] == "pump:default:abc"
            assert pump_module.is_queue_pump_paused("default") is False

    def test_producer_gate_pause_until_resume(self):
        import backend.db_periodic_task.dispatch.producer as producer_module

        store = {}

        def redis_set(key, value, ex=None, **_kwargs):
            store[key] = {"value": value, "ex": ex}
            return True

        def redis_get(key):
            item = store.get(key)
            return None if item is None else item["value"]

        def redis_ttl(key):
            item = store.get(key)
            if item is None:
                return -2
            return -1 if item["ex"] is None else int(item["ex"])

        def release_side_effect(keys, args, **kwargs):
            item = store.get(keys[0])
            if item and item["value"] == args[0]:
                store.pop(keys[0])
                return 1
            return 0

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        redis_client.get.side_effect = redis_get
        redis_client.ttl.side_effect = redis_ttl
        with patch.object(producer_module, "_release_lock_script", MagicMock(side_effect=release_side_effect)), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ):
            info = producer_module.pause_queue_producer("default", seconds=None)
            assert info == {"namespace": "default", "paused": True, "ttl_seconds": None}
            assert producer_module.is_queue_producer_paused("default") is True
            assert producer_module.queue_producer_pause_ttl("default") == -1
            assert store["dispatch:default:producer_gate"]["value"] == producer_module.PRODUCER_PAUSE_OWNER
            assert store["dispatch:default:producer_gate"]["ex"] is None

            assert producer_module.resume_queue_producer("default") is True
            assert producer_module.is_queue_producer_paused("default") is False
            assert "dispatch:default:producer_gate" not in store

    def test_producer_gate_ttl_auto_expires(self):
        import backend.db_periodic_task.dispatch.producer as producer_module

        store = {}

        def redis_set(key, value, ex=None, **_kwargs):
            store[key] = {"value": value, "ex": ex}
            return True

        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ):
            info = producer_module.pause_queue_producer("default", seconds=1.9)
            assert info == {"namespace": "default", "paused": True, "ttl_seconds": 2}
            assert store["dispatch:default:producer_gate"]["ex"] == 2

    def test_producer_gate_requires_namespace(self):
        import backend.db_periodic_task.dispatch.producer as producer_module

        with pytest.raises(ValueError):
            producer_module.pause_queue_producer("")
        with pytest.raises(ValueError):
            producer_module.resume_queue_producer("")

    def test_record_pump_ticks_skipped_backfills_gap(self, pump_module):
        with patch.object(pump_module, "_read_pump_ticks_skipped_baseline", return_value=-1), patch.object(
            pump_module.DispatchMetrics, "record_queue_event"
        ) as record:
            missed = pump_module._record_pump_ticks_skipped(SimpleNamespace(namespace="dummy"), 105, {"tick_id": 100})
        assert missed == 4
        record.assert_called_once_with("dummy", "pump_ticks_skipped", 4, timestamp=105 * 10)

    def test_record_pump_ticks_skipped_ignores_pause_baseline(self, pump_module):
        with patch.object(pump_module, "_read_pump_ticks_skipped_baseline", return_value=104), patch.object(
            pump_module.DispatchMetrics, "record_queue_event"
        ) as record:
            missed = pump_module._record_pump_ticks_skipped(SimpleNamespace(namespace="dummy"), 105, {"tick_id": 100})
        assert missed == 0
        record.assert_not_called()

    @pytest.mark.parametrize("paused", [True, False])
    def test_lock_skip_records_pump_lock_contention_only_when_not_paused(self, pump_module, paused):
        queue = SimpleNamespace(namespace="dummy")
        with patch.object(pump_module, "_try_acquire_pump_lock", return_value=False), patch.object(
            pump_module, "is_queue_pump_paused", return_value=paused
        ), patch.object(pump_module.DispatchMetrics, "record_queue_event") as record, patch.object(
            pump_module, "_pump_queue"
        ) as pump_queue:
            assert pump_module._pump_queue_with_lock(queue, time.monotonic() + 10, 200, 11) == 0

        if paused:
            record.assert_not_called()
        else:
            record.assert_called_once_with("dummy", "pump_lock_contention", timestamp=200 * 10)
        pump_queue.assert_not_called()

    def test_pause_and_resume_advance_missed_baseline(self, pump_module):
        store = {}

        def redis_set(key, value, nx=False, ex=None, **_kwargs):
            if nx and key in store:
                return False
            store[key] = {"value": value, "ex": ex}
            return True

        def redis_get(key):
            item = store.get(key)
            return None if item is None else item["value"]

        def release_side_effect(keys, args, **kwargs):
            key = keys[0]
            item = store.get(key)
            if item and item["value"] == args[0]:
                store.pop(key)
                return 1
            return 0

        release_script = MagicMock(side_effect=release_side_effect)
        baseline_key = pump_module._pump_ticks_skipped_baseline_key("default")
        redis_client = MagicMock()
        redis_client.set.side_effect = redis_set
        redis_client.get.side_effect = redis_get
        redis_client.ttl.return_value = -1
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis_client,
        ), patch.object(pump_module, "_release_lock_script", release_script), patch(
            "backend.db_periodic_task.dispatch.pump.tick_id", side_effect=[50, 55]
        ):
            pump_module.pause_queue_pump("default", seconds=None)
            assert store[baseline_key]["value"] == 50
            assert pump_module.resume_queue_pump("default") is True
            assert store[baseline_key]["value"] == 55


class TestQueueFIFO:
    def test_enqueue_score_uses_ready_at_without_priority_offset(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        job = TestPumpQueue._job(ready_at=123.5)
        script = MagicMock(return_value=EnqueueStatus.ACCEPTED)
        with patch.object(QueueAdmission, "_enqueue_script", script):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=[job],
                dedupe_enqueue=False,
                queue_wait_ttls=[86400],
                max_admitted_jobs=10,
            )

        assert statuses == [EnqueueStatus.ACCEPTED]
        assert script.call_args.kwargs["args"][8] == 123.5


class TestQueueAdmission:
    def test_capacity_rejected_status(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        job = TestPumpQueue._job()
        script = MagicMock(return_value=EnqueueStatus.CAPACITY_REJECTED)
        with patch.object(QueueAdmission, "_enqueue_script", script):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=[job],
                dedupe_enqueue=False,
                queue_wait_ttls=[86400],
                max_admitted_jobs=1,
            )
        assert statuses == [EnqueueStatus.CAPACITY_REJECTED]

    def test_expired_deadline_returns_deadline_expired_not_capacity(self):
        """P2-8: an expired wait deadline is not a full-queue signal."""
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        job = TestPumpQueue._job(ready_at=100.0, wait_deadline_at=99.0)  # expired vs patched now=100.0
        script = MagicMock()
        with patch.object(QueueAdmission, "_enqueue_script", script), patch(
            "backend.db_periodic_task.dispatch.admission.time.time",
            return_value=100.0,
        ):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=[job],
                dedupe_enqueue=False,
                queue_wait_ttls=[60],
                max_admitted_jobs=10,
            )

        # The expired job is rejected with its own status and never reaches Lua.
        assert statuses == [EnqueueStatus.DEADLINE_EXPIRED]
        script.assert_not_called()

    def test_enqueue_lua_receives_cumulative_metric_keys(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        job = TestPumpQueue._job()
        script = MagicMock(return_value=EnqueueStatus.ACCEPTED)
        with patch.object(QueueAdmission, "_enqueue_script", script), patch(
            "backend.db_periodic_task.dispatch.admission.time.time",
            return_value=120.0,
        ), patch(
            "backend.db_periodic_task.dispatch.metrics.time.time",
            return_value=120.0,
        ):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=[job],
                dedupe_enqueue=True,
                queue_wait_ttls=[86400],
                max_admitted_jobs=10,
            )

        assert statuses == [EnqueueStatus.ACCEPTED]
        keys = script.call_args.kwargs["keys"]
        args = script.call_args.kwargs["args"]
        assert keys[2:4] == [
            "dispatch:default:metrics:cumulative:task:task",
            "dispatch:default:metrics:cumulative:events",
        ]
        assert keys[4] == "dispatch:default:task_counts"
        assert keys[6] == "dispatch:default:metrics:cumulative:started_at"
        assert args[2] == "task"
        assert args[4] == 120.0
        assert args[5] == TASK_COUNTS_TTL_SECONDS

    def test_future_ready_at_delays_start_of_queue_wait_ttl(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        job = TestPumpQueue._job(ready_at=130.0, wait_deadline_at=0.0)
        script = MagicMock(return_value=EnqueueStatus.ACCEPTED)
        with patch.object(QueueAdmission, "_enqueue_script", script), patch(
            "backend.db_periodic_task.dispatch.admission.time.time",
            return_value=100.0,
        ):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=[job],
                dedupe_enqueue=False,
                queue_wait_ttls=[60],
                max_admitted_jobs=10,
            )

        assert statuses == [EnqueueStatus.ACCEPTED]
        args = script.call_args.kwargs["args"]
        snapshot = json.loads(args[9])
        assert snapshot["wait_deadline_at"] == 190.0
        assert args[10] == 90

    def test_batch_admission_returns_ordered_statuses_in_one_script(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus

        jobs = [TestPumpQueue._job(job_id=f"task:{index}", work_item_id=str(index)) for index in range(3)]
        expected = [
            EnqueueStatus.ACCEPTED,
            EnqueueStatus.DUPLICATE,
            EnqueueStatus.CAPACITY_REJECTED,
        ]
        script = MagicMock(return_value=expected)
        with patch.object(QueueAdmission, "_enqueue_script", script):
            statuses = QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=jobs,
                dedupe_enqueue=True,
                queue_wait_ttls=[60] * len(jobs),
                max_admitted_jobs=10,
            )

        assert statuses == expected
        script.assert_called_once()
        # 7 base keys: queue state, cumulative metrics, task counts, gate, generation.
        assert len(script.call_args.kwargs["keys"]) == 7 + 2 * len(jobs)
        assert script.call_args.kwargs["args"][6] == len(jobs)

    def test_batch_admission_rejects_more_than_25_jobs(self):
        from backend.db_periodic_task.dispatch.admission import QueueAdmission

        jobs = [
            TestPumpQueue._job(job_id=f"task:{index}", work_item_id=str(index))
            for index in range(DISPATCH_LUA_BATCH_SIZE + 1)
        ]
        with pytest.raises(ValueError, match="admission batch"):
            QueueAdmission.enqueue_jobs(
                queue_cls=DispatchQueue,
                jobs=jobs,
                dedupe_enqueue=True,
                queue_wait_ttls=[60] * len(jobs),
                max_admitted_jobs=100,
            )


class TestQueueCleanup:
    def test_finalize_job_uses_one_atomic_lifecycle_script(self):
        script = MagicMock(return_value=1)
        with patch("backend.db_periodic_task.dispatch.lifecycle._finalize_script", script):
            QueueLifecycle.finalize_job(
                queue_cls=DispatchQueue,
                job_id="task:item",
                task_key="task",
                work_item_id="item",
            )

        script.assert_called_once()
        assert script.call_args.kwargs["keys"] == [
            "dispatch:default:job:task:item",
            "dispatch:default:reserved",
            "dispatch:default:dedupe:task:item",
            "dispatch:default:task_counts",
        ]
        assert script.call_args.kwargs["args"][0:2] == ["task:item", "reserved:task"]
        assert script.call_args.kwargs["args"][2] == TASK_COUNTS_TTL_SECONDS

    def test_requeue_uses_one_atomic_lifecycle_script(self):
        job = TestPumpQueue._job()
        script = MagicMock(return_value=1)
        with patch("backend.db_periodic_task.dispatch.lifecycle._requeue_script", script):
            assert (
                QueueLifecycle.requeue(
                    queue_cls=DispatchQueue,
                    job=job,
                    ready_at=job.ready_at,
                    queue_wait_ttl=60,
                )
                is RequeueResult.REQUEUED
            )

        script.assert_called_once()
        assert script.call_args.kwargs["keys"] == [
            "dispatch:default:job:task:item",
            "dispatch:default:reserved",
            "dispatch:default:pending",
            "dispatch:default:task_counts",
        ]
        assert script.call_args.kwargs["args"][4:6] == ["reserved:task", "pending:task"]
        assert script.call_args.kwargs["args"][6] == TASK_COUNTS_TTL_SECONDS

    def test_requeue_after_reservation_starts_fresh_wait_stint(self):
        """Reservation persists jobs with a cleared deadline; requeue grants a fresh wait budget."""
        job = TestPumpQueue._job(wait_deadline_at=0.0)
        script = MagicMock(return_value=1)
        with patch("backend.db_periodic_task.dispatch.lifecycle._requeue_script", script), patch(
            "backend.db_periodic_task.dispatch.lifecycle.time.time",
            return_value=100.0,
        ):
            assert (
                QueueLifecycle.requeue(
                    queue_cls=DispatchQueue,
                    job=job,
                    ready_at=130.0,
                    queue_wait_ttl=60,
                )
                is RequeueResult.REQUEUED
            )

        args = script.call_args.kwargs["args"]
        snapshot = json.loads(args[1])
        assert snapshot["wait_deadline_at"] == 190.0
        assert args[2:4] == [90, 130.0]

    def test_requeue_preserves_existing_deadline(self):
        job = TestPumpQueue._job(wait_deadline_at=150.0)
        script = MagicMock(return_value=1)
        with patch("backend.db_periodic_task.dispatch.lifecycle._requeue_script", script), patch(
            "backend.db_periodic_task.dispatch.lifecycle.time.time",
            return_value=100.0,
        ):
            assert (
                QueueLifecycle.requeue(
                    queue_cls=DispatchQueue,
                    job=job,
                    ready_at=130.0,
                    queue_wait_ttl=60,
                )
                is RequeueResult.REQUEUED
            )

        args = script.call_args.kwargs["args"]
        snapshot = json.loads(args[1])
        assert snapshot["wait_deadline_at"] == 150.0
        assert args[2:4] == [50, 130.0]

    def test_requeue_reports_slot_lost_when_job_already_finalized(self):
        """P2-9: a requeue that finds no reserved member must not be reported as success."""
        job = TestPumpQueue._job(wait_deadline_at=0.0)
        script = MagicMock(return_value=0)  # ZREM removed nothing
        with patch("backend.db_periodic_task.dispatch.lifecycle._requeue_script", script), patch(
            "backend.db_periodic_task.dispatch.lifecycle.time.time",
            return_value=100.0,
        ):
            assert (
                QueueLifecycle.requeue(
                    queue_cls=DispatchQueue,
                    job=job,
                    ready_at=130.0,
                    queue_wait_ttl=60,
                )
                is RequeueResult.SLOT_LOST
            )

        # The Lua was still invoked (so a single atomic no-op happened), and the
        # caller learns the requeue failed -> its finalize path still runs.
        script.assert_called_once()

    def test_ephemeral_queue_targets_namespace_keys_without_registering(self):
        from backend.db_periodic_task.dispatch.queue import DISPATCH_QUEUE_REGISTRY

        queue_cls = DispatchQueue.ephemeral_queue_for_namespace("gone")
        assert queue_cls is not DispatchQueue
        assert queue_cls.namespace == "gone"
        assert queue_cls.reserved_key() == "dispatch:gone:reserved"
        assert queue_cls.pending_key() == "dispatch:gone:pending"
        assert queue_cls.task_counts_key() == "dispatch:gone:task_counts"
        assert queue_cls.dedupe_key("task", "item") == "dispatch:gone:dedupe:task:item"
        assert DISPATCH_QUEUE_REGISTRY.get("gone") is None

        # Empty namespace still resolves to the default namespace keys.
        assert DispatchQueue.ephemeral_queue_for_namespace("").namespace == "default"

    def test_reap_persists_cursor_when_scan_limit_hit(self):
        pending_members = [(b"task:%d" % i, 1.0) for i in range(100)]
        redis = MagicMock()
        redis.get.return_value = None  # no persisted cursors yet
        redis.zscan.side_effect = [
            (5, pending_members),
            (10, pending_members),
            (0, []),
        ]
        redis.mget.return_value = [b"payload"] * 100

        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.global_conn",
            return_value=redis,
        ):
            assert OrphanReaper.reap_orphaned_queue_jobs(DispatchQueue) == 0

        assert redis.zscan.call_args_list == [
            call("dispatch:default:pending", 0, count=100),
            call("dispatch:default:pending", 5, count=100),
            call("dispatch:default:reserved", 0, count=100),
        ]
        # scan_limit hit mid-iteration -> resume point persisted for the next tick
        redis.set.assert_called_once_with(
            "dispatch:default:pending:reap_cursor",
            "10",
            ex=REAP_CURSOR_TTL_SECONDS,
        )
        # the reserved scan completed a full pass -> its cursor is cleared
        redis.delete.assert_called_with("dispatch:default:reserved:reap_cursor")

    def test_reap_resumes_from_persisted_cursor_and_reaps_deep_orphan(self):
        redis = MagicMock()
        redis.hkeys.return_value = [b"task"]

        def _get(key):
            if key == "dispatch:default:pending:reap_cursor":
                return b"5"
            return None

        redis.get.side_effect = _get
        redis.zscan.side_effect = [
            (0, [(b"task:deep", 1.0)]),  # pending resumes at cursor 5, finishes
            (0, []),  # reserved empty
        ]
        redis.mget.return_value = [None]  # the deep member's payload is gone

        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.global_conn",
            return_value=redis,
        ), patch.object(OrphanReaper, "discard_orphaned_job", return_value=True) as discard:
            assert OrphanReaper.reap_orphaned_queue_jobs(DispatchQueue) == 1

        # The next tick continues from the stored cursor instead of the head.
        assert redis.zscan.call_args_list[0] == call("dispatch:default:pending", 5, count=100)
        discard.assert_called_once()
        assert discard.call_args.kwargs["task_key"] == "task"
        assert discard.call_args.kwargs["work_item_id"] == "deep"
        # Both scans completed full passes -> both cursors cleared.
        redis.delete.assert_any_call("dispatch:default:pending:reap_cursor")
        redis.delete.assert_any_call("dispatch:default:reserved:reap_cursor")

    def test_reap_persists_cursor_when_deadline_hits_mid_scan(self):
        redis = MagicMock()
        redis.get.return_value = None
        redis.zscan.side_effect = [
            (5, [(b"task:%d" % i, 1.0) for i in range(100)]),
            (9, [(b"task:%d" % i, 1.0) for i in range(100)]),
        ]
        redis.mget.return_value = [b"payload"] * 100

        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.global_conn",
            return_value=redis,
        ), patch("backend.db_periodic_task.dispatch.reaper.time.monotonic", side_effect=[5.0, 6.0]):
            assert OrphanReaper.reap_orphaned_queue_jobs(DispatchQueue, deadline_at=5.5) == 0

        # Budget exhausted: the cursor from the last page is kept for the next tick.
        redis.set.assert_called_once_with(
            "dispatch:default:pending:reap_cursor",
            "5",
            ex=REAP_CURSOR_TTL_SECONDS,
        )


class TestRateLimitRequeue:
    @staticmethod
    def _task(max_retries: int):
        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType

        class _Task(DispatchTask):
            task_key = "test.ratelimit"
            namespace = "test"

            def execute(self, item, *, job=None, overrides=None):
                return DispatchOutcome(
                    outcome=DispatchOutcomeType.REQUEUED,
                    should_requeue=True,
                    requeue_cooldown_seconds=5,
                    exhausted_outcome=DispatchOutcomeType.REQUEUE_EXHAUSTED,
                )

            def build_job(self, item, *, overrides=None, ready_at=None, config=None):
                return TestPumpQueue._job(task_key=self.task_key)

        config = DispatchTaskConfig(enabled=True, max_requeue_attempts=max_retries, queue_wait_ttl_seconds=70)
        return _Task(config=config)

    def test_fresh_wait_stints_are_bounded_by_retry_cap(self):
        job = TestPumpQueue._job(wait_deadline_at=0.0, retry_count=0)
        task = self._task(max_retries=2)
        with patch.object(task, "requeue_job", return_value=True) as requeue_job, patch.object(task, "record_outcome"):
            assert task.execute_from_job(job) is True

        requeued = requeue_job.call_args.args[0]
        assert requeued.retry_count == 1
        assert job.retry_count == 0
        requeue_job.assert_called_once()
        assert requeue_job.call_args.kwargs["queue_wait_ttl"] == 70

        job.retry_count = 2
        with patch.object(task, "requeue_job", return_value=True) as requeue_job, patch.object(
            task, "record_outcome"
        ) as record_outcome, patch.object(task, "on_execute_complete") as on_complete:
            assert task.execute_from_job(job) is False

        requeue_job.assert_not_called()
        on_complete.assert_called_once()
        record_outcome.assert_called_once()
        assert record_outcome.call_args.args[0] == DispatchOutcomeType.REQUEUE_EXHAUSTED

    def test_failed_requeue_records_exhausted_outcome(self):
        job = TestPumpQueue._job(wait_deadline_at=0.0, retry_count=0)
        task = self._task(max_retries=3)
        with patch.object(task, "requeue_job", return_value=False) as requeue_job, patch.object(
            task, "record_outcome"
        ) as record_outcome, patch.object(task, "on_execute_complete") as on_complete:
            assert task.execute_from_job(job) is False

        requeue_job.assert_called_once()
        on_complete.assert_called_once()
        record_outcome.assert_called_once()
        assert record_outcome.call_args.args[0] == DispatchOutcomeType.REQUEUE_EXHAUSTED

    def test_expired_wait_deadline_records_exhausted_outcome(self):
        job = TestPumpQueue._job(wait_deadline_at=1.0, retry_count=0)
        task = self._task(max_retries=3)
        with patch.object(task, "record_outcome") as record_outcome, patch.object(
            task, "on_execute_complete"
        ) as on_complete, patch("backend.db_periodic_task.dispatch.reaper.OrphanReaper.discard_orphaned_job"):
            assert task.execute_from_job(job) is False

        on_complete.assert_called_once()
        record_outcome.assert_called_once()
        assert record_outcome.call_args.args[0] == DispatchOutcomeType.REQUEUE_EXHAUSTED

    def test_missing_reserved_membership_records_exhausted_outcome(self):
        job = TestPumpQueue._job(wait_deadline_at=0.0, retry_count=0)
        task = self._task(max_retries=3)
        with patch.object(task, "record_outcome") as record_outcome, patch.object(
            task, "on_execute_complete"
        ) as on_complete, patch(
            "backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle._eval_requeue",
            return_value=0,
        ):
            assert task.execute_from_job(job) is False

        on_complete.assert_called_once()
        record_outcome.assert_called_once()
        assert record_outcome.call_args.args[0] == DispatchOutcomeType.REQUEUE_EXHAUSTED

    def test_purge_job_runs_one_atomic_script(self):
        script = MagicMock(return_value=[1, 0])  # pending hit, reserved miss
        with patch("backend.db_periodic_task.dispatch.reaper._purge_job_script", script):
            assert OrphanReaper.purge_job(DispatchQueue, "task:item", task_key="task") == (1, 0)

        script.assert_called_once()
        assert script.call_args.kwargs["keys"] == [
            "dispatch:default:pending",
            "dispatch:default:reserved",
            "dispatch:default:task_counts",
        ]
        assert script.call_args.kwargs["args"] == [
            "task:item",
            "pending:task",
            "reserved:task",
            TASK_COUNTS_TTL_SECONDS,
        ]
        assert script.call_args.kwargs["client"] is not None

    def test_pending_count_for_task_reads_hash(self):
        client = MagicMock()
        client.hget.return_value = b"3"
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client) as conn:
            assert DispatchQueue.pending_count_for_task("task") == 3
        conn.return_value.hget.assert_called_once_with("dispatch:default:task_counts", "pending:task")

    @pytest.mark.parametrize(
        "method,count,expected",
        [
            ("has_pending_for_task", 0, False),
            ("has_pending_for_task", 2, True),
            # Fail closed: an unreadable count (-1) must look *busy*, never idle.
            ("has_pending_for_task", -1, True),
            ("has_reserved_for_task", -1, True),
            ("has_reserved_for_task", 0, False),
        ],
    )
    def test_has_work_for_task_fails_closed_on_unreadable_count(self, method, count, expected):
        check = getattr(DispatchQueue, method)
        count_method = "pending_count_for_task" if method.startswith("has_pending") else "reserved_count_for_task"
        with patch.object(DispatchQueue, count_method, return_value=count):
            assert check("task") is expected

    def test_rebuild_task_counts_rewrites_hash(self):
        zscan_pages = [
            (0, [(b"task:a", 1.0), (b"task:b", 2.0)]),
        ]
        reserved_pages = [
            (0, [(b"task:a", 3.0)]),
        ]
        replace_script = MagicMock(return_value=1)
        redis = MagicMock()
        redis.hkeys.return_value = [b"task"]
        redis.zscan.side_effect = [*zscan_pages, *reserved_pages]
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis,
        ), patch(
            "backend.db_periodic_task.dispatch.task_counts._replace_task_counts_script",
            replace_script,
        ):
            rebuilt = TaskCounts.rebuild(DispatchQueue, scan_pause_seconds=0)

        assert rebuilt["pending:task"] == 2
        assert rebuilt["reserved:task"] == 1
        replace_script.assert_called_once()
        assert replace_script.call_args.kwargs["keys"] == [
            "dispatch:default:pending",
            "dispatch:default:reserved",
            "dispatch:default:task_counts",
        ]
        assert replace_script.call_args.kwargs["args"] == [
            2,
            1,
            2,
            TASK_COUNTS_TTL_SECONDS,
            "pending:task",
            2,
            "reserved:task",
            1,
        ]

    def test_rebuild_task_counts_aborts_on_deadline_without_write(self):
        redis = MagicMock()
        redis.hkeys.return_value = [b"task"]
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.task_counts.time.monotonic",
            return_value=100.0,
        ), patch.object(TaskCounts, "_replace_if_current") as replace:
            assert TaskCounts.rebuild(DispatchQueue, deadline_at=50.0) is None
        replace.assert_not_called()

    def test_rebuild_task_counts_discards_changed_queue(self):
        replace_script = MagicMock(return_value=0)
        redis = MagicMock()
        redis.hkeys.return_value = [b"task"]
        redis.zscan.side_effect = [
            (0, [(b"task:a", 1.0)]),
            (0, []),
        ]
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis,
        ), patch(
            "backend.db_periodic_task.dispatch.task_counts._replace_task_counts_script",
            replace_script,
        ):
            assert TaskCounts.rebuild(DispatchQueue, scan_pause_seconds=0) is None

        replace_script.assert_called_once()

    def test_rebuild_buckets_unresolved_members_instead_of_aborting(self):
        """P2-10: members with no registered task prefix must not stall the whole rebuild."""
        replace_script = MagicMock(return_value=1)
        redis = MagicMock()
        redis.hkeys.return_value = [b"task"]
        redis.zscan.side_effect = [
            (0, [(b"task:a", 1.0), (b"ghost-task:x", 2.0)]),  # pending: 1 known + 1 unresolved
            (0, [(b"ghost-task:y", 3.0)]),  # reserved: 1 unresolved
        ]
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=redis), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=redis,
        ), patch(
            "backend.db_periodic_task.dispatch.task_counts._replace_task_counts_script",
            replace_script,
        ):
            rebuilt = TaskCounts.rebuild(DispatchQueue, scan_pause_seconds=0)

        # The rebuild completes and totals still reconcile with ZCARD.
        assert rebuilt is not None
        assert rebuilt["pending:task"] == 1
        assert rebuilt["pending:__unresolved__"] == 1
        assert rebuilt["reserved:__unresolved__"] == 1
        args = replace_script.call_args.kwargs["args"]
        assert args[0:2] == [2, 1]  # expected pending=2, reserved=1 (unresolved included)

    def test_resolve_task_key_from_job_id_prefers_longest_prefix(self):
        registered = ["task", "task:nested"]
        assert resolve_task_key_from_job_id("task:nested:item", registered) == "task:nested"
        assert resolve_task_key_from_job_id("task:item", registered) == "task"

    def test_task_counts_daily_and_requested_markers(self):
        client = MagicMock()
        client.exists.side_effect = [0, 1]
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            assert TaskCounts.hard_rebuild_due(DispatchQueue) is True
            assert TaskCounts.rebuild_requested(DispatchQueue) is True

        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client) as conn:
            assert TaskCounts.request_rebuild(DispatchQueue, "count_drift") is True
        conn.return_value.set.assert_called_once_with(
            "dispatch:default:task_counts_rebuild_requested",
            "count_drift",
            ex=TASK_COUNTS_REBUILD_REQUEST_TTL_SECONDS,
        )

    def test_task_counts_attempt_backoff_and_success_markers(self):
        with patch(
            "backend.db_periodic_task.dispatch.task_counts.try_acquire_ttl_gate",
            return_value=True,
        ) as marker:
            assert TaskCounts.try_start_rebuild(DispatchQueue) is True
        marker.assert_called_once()
        assert marker.call_args.args == (
            "dispatch:default:task_counts_rebuild_attempt",
            TASK_COUNTS_REBUILD_RETRY_SECONDS,
        )
        assert marker.call_args.kwargs["client"] is not None

        pipeline = MagicMock()
        client = MagicMock()
        client.pipeline.return_value = pipeline
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            assert TaskCounts.mark_rebuilt(DispatchQueue) is True
        pipeline.set.assert_called_once_with(
            "dispatch:default:task_counts_rebuilt",
            "1",
            ex=TASK_COUNTS_REBUILD_FORCE_SECONDS,
        )
        pipeline.delete.assert_called_once_with(
            "dispatch:default:task_counts_rebuild_requested",
            "dispatch:default:task_counts_rebuild_attempt",
        )
        pipeline.execute.assert_called_once()

    @pytest.mark.parametrize(
        "pending_z,reserved_z,members,expected",
        [
            # Global totals disagree with the hash field sums.
            (5, 0, {b"pending:task": b"3"}, True),
            # Invalid field values are drift evidence.
            (0, 0, {b"pending:task": b"-1"}, True),
            (0, 0, {b"pending:task": b"not-int"}, True),
            # Consistent totals are healthy.
            (2, 1, {b"pending:task": b"2", b"reserved:task": b"1"}, False),
        ],
    )
    def test_task_counts_counts_drifted(self, pending_z, reserved_z, members, expected):
        client = MagicMock()
        client.hgetall.return_value = members
        with patch.object(DispatchQueue, "pending_count", return_value=pending_z), patch.object(
            DispatchQueue, "reserved_count", return_value=reserved_z
        ), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=client,
        ):
            assert TaskCounts.counts_drifted(DispatchQueue) is expected

    def test_discard_orphaned_job_also_deletes_dedupe(self):
        job = TestPumpQueue._job(namespace="default")
        pipeline = MagicMock()
        pipeline.execute.return_value = [1, 1]
        client = MagicMock()
        client.pipeline.return_value = pipeline
        with patch.object(DispatchQueue, "get_job", return_value=job), patch.object(
            DispatchQueue, "queue_for_namespace", return_value=DispatchQueue
        ), patch.object(OrphanReaper, "purge_job", return_value=(0, 1)) as purge, patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=client,
        ), patch.object(
            DispatchQueue, "record_outcome"
        ) as record_outcome:
            assert OrphanReaper.discard_orphaned_job(
                DispatchQueue,
                job.job_id,
                task_key=job.task_key,
                namespace=job.namespace,
                work_item_id=job.work_item_id,
            )

        purge.assert_called_once_with(DispatchQueue, job.job_id, task_key=job.task_key)
        pipeline.delete.assert_any_call("dispatch:default:job:task:item")
        pipeline.delete.assert_any_call("dispatch:default:dedupe:task:item")
        record_outcome.assert_called_once()
        assert record_outcome.call_args.args[1].value == "expired"

    def test_discard_orphaned_job_unknown_namespace_deletes_dedupe_only_on_hit(self):
        pipeline = MagicMock()
        pipeline.execute.return_value = [1, 1]
        hit_queue = MagicMock()
        hit_queue.namespace = "ai"
        miss_queue = MagicMock()
        miss_queue.namespace = "dummy"
        client = MagicMock()
        client.pipeline.return_value = pipeline
        with patch.object(DispatchQueue, "get_job", return_value=None), patch.object(
            DispatchQueue, "registered_queues", return_value=[miss_queue, hit_queue]
        ), patch.object(
            OrphanReaper,
            "purge_job",
            side_effect=lambda queue_cls, job_id, **_kwargs: (1, 0) if queue_cls is hit_queue else (0, 0),
        ), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=client,
        ), patch.object(
            DispatchQueue, "record_outcome"
        ):
            assert (
                OrphanReaper.discard_orphaned_job(
                    DispatchQueue,
                    "task:item",
                    task_key="task",
                    work_item_id="item",
                )
                is True
            )

        dedupe_deletes = [c.args[0] for c in pipeline.delete.call_args_list if ":dedupe:" in c.args[0]]
        # No cross-namespace broadcast: only the queue where the member lived.
        assert dedupe_deletes == ["dispatch:ai:dedupe:task:item"]
        pipeline.delete.assert_any_call("dispatch:ai:job:task:item")

    def test_discard_orphaned_job_unknown_namespace_without_hit_keeps_dedupe(self):
        miss_queue = MagicMock()
        client = MagicMock()
        with patch.object(DispatchQueue, "get_job", return_value=None), patch.object(
            DispatchQueue, "registered_queues", return_value=[miss_queue]
        ), patch.object(OrphanReaper, "purge_job", return_value=(0, 0)), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=client,
        ):
            assert (
                OrphanReaper.discard_orphaned_job(
                    DispatchQueue,
                    "task:item",
                    task_key="task",
                    work_item_id="item",
                )
                is True
            )

        client.pipeline.assert_not_called()

    def test_discard_orphaned_job_unregistered_namespace_uses_ephemeral_queue(self):
        job = TestPumpQueue._job(namespace="ghost")
        ephemeral = MagicMock()
        ephemeral.namespace = "ghost"
        ephemeral.job_key.return_value = "dispatch:ghost:job:task:item"
        pipeline = MagicMock()
        pipeline.execute.return_value = [1, 1]
        client = MagicMock()
        client.pipeline.return_value = pipeline
        with patch.object(DispatchQueue, "get_job", return_value=job), patch.object(
            DispatchQueue, "queue_for_namespace", return_value=None
        ), patch.object(
            DispatchQueue, "ephemeral_queue_for_namespace", return_value=ephemeral
        ) as make_ephemeral, patch.object(
            DispatchQueue, "registered_queues"
        ) as registered_queues, patch.object(
            OrphanReaper, "purge_job", return_value=(0, 1)
        ) as purge, patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=client,
        ), patch.object(
            DispatchQueue, "record_outcome"
        ):
            assert (
                OrphanReaper.discard_orphaned_job(
                    DispatchQueue,
                    job.job_id,
                    task_key=job.task_key,
                    namespace="ghost",
                    work_item_id=job.work_item_id,
                )
                is True
            )

        make_ephemeral.assert_called_once_with("ghost")
        registered_queues.assert_not_called()  # no broadcast when the namespace is known
        purge.assert_called_once_with(ephemeral, job.job_id, task_key=job.task_key)
        pipeline.delete.assert_any_call("dispatch:ghost:job:task:item")
        pipeline.delete.assert_any_call("dispatch:ghost:dedupe:task:item")

    def test_reconcile_registered_metadata_drops_unknown_task_and_queue(self):
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

        raw = {
            b"alive.task": b'{"task_key":"alive.task","namespace":"alive"}',
            b"gone.task": b'{"task_key":"gone.task","namespace":"alive"}',
            b"bad.queue": b'{"task_key":"bad.queue","namespace":"missing"}',
        }
        alive = MagicMock()
        alive.namespace = "alive"
        previous = {
            key: DISPATCH_REGISTRY.pop(key)
            for key in list(DISPATCH_REGISTRY)
            if key.startswith(("alive.", "gone.", "bad."))
        }
        DISPATCH_REGISTRY["alive.task"] = alive
        DISPATCH_REGISTRY["bad.queue"] = alive
        try:
            client = MagicMock()
            client.hgetall.return_value = raw
            client.hdel.return_value = 2
            with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
                DispatchQueue, "ensure_queues_loaded"
            ), patch.dict(
                "backend.db_periodic_task.dispatch.queue.DISPATCH_QUEUE_REGISTRY",
                {"alive": MagicMock()},
                clear=True,
            ):
                removed = DispatchQueue.reconcile_registered_metadata()
        finally:
            DISPATCH_REGISTRY.pop("alive.task", None)
            DISPATCH_REGISTRY.pop("bad.queue", None)
            DISPATCH_REGISTRY.update(previous)

        assert removed == 2
        removed_fields = set(client.hdel.call_args.args[1:])
        assert removed_fields == {"gone.task", "bad.queue"}

    def test_register_task_metadata_triggers_reconcile(self):
        client = MagicMock()
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client) as conn, patch.object(
            DispatchQueue, "reconcile_registered_metadata"
        ) as reconcile:
            DispatchQueue.register_task_metadata("task", {"task_key": "task", "namespace": "ai"})
        conn.return_value.hset.assert_called_once()
        reconcile.assert_called_once()

    def test_resolve_reserved_ttl_uses_execution_timeout_plus_margin(self):
        from backend.db_periodic_task.dispatch.config import RESERVED_TTL_MARGIN_SECONDS, DispatchTaskConfig

        cfg = DispatchTaskConfig(execution_timeout_seconds=3600)
        assert cfg.resolve_reserved_record_ttl_seconds() == 3600 + RESERVED_TTL_MARGIN_SECONDS

    def test_task_counts_uses_one_hmget(self):
        client = MagicMock()
        client.hmget.return_value = [b"7", b"2"]
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client) as conn:
            assert DispatchQueue.task_counts("task") == (7, 2)

        conn.return_value.hmget.assert_called_once_with(
            DispatchQueue.task_counts_key(),
            ["pending:task", "reserved:task"],
        )

    def test_base_queue_has_no_congestion_outcomes(self):
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType

        assert DispatchQueue.is_congestion_outcome(DispatchOutcomeType.REQUEUED) is False
        assert DispatchQueue.is_congestion_outcome(DispatchOutcomeType.ERROR) is False

    def test_record_outcome_writes_congestion_when_hook_matches(self):
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType

        class CongestedQueue(DispatchQueue):
            @classmethod
            def is_congestion_outcome(cls, outcome):
                return outcome == DispatchOutcomeType.ERROR

        with patch("backend.db_periodic_task.dispatch.metrics.DispatchMetrics.record_task_outcome") as record_outcome:
            CongestedQueue.record_outcome("task", DispatchOutcomeType.ERROR)
        assert record_outcome.call_args.kwargs["congested"] is True

        with patch("backend.db_periodic_task.dispatch.metrics.DispatchMetrics.record_task_outcome") as record_outcome:
            CongestedQueue.record_outcome("task", DispatchOutcomeType.SUCCESS)
        assert record_outcome.call_args.kwargs["congested"] is False


class TestDispatchRegistry:
    def test_duplicate_task_key_raises(self):
        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY, register_dispatch_task

        dup_key = "test.registry.duplicate_key"
        DISPATCH_REGISTRY.pop(dup_key, None)

        class RegistryTestQueueConfig(DispatchQueueConfig):
            namespace: ClassVar[str] = "test"

        class RegistryTestQueue(DispatchQueue):
            config_cls = RegistryTestQueueConfig

        class RegistryTestConfig(DispatchTaskConfig):
            task_key: ClassVar[str] = dup_key

        with patch.object(RegistryTestQueue, "register_task_metadata"):

            @register_dispatch_task(config_cls=RegistryTestConfig)
            class FirstTask(DispatchTask):
                queue_cls = RegistryTestQueue

                def execute(self, item, *, job=None, overrides=None):
                    return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS)

                def build_job(self, item, *, overrides=None, ready_at=None, config=None):
                    return TestPumpQueue._job(task_key=dup_key)

            try:
                with pytest.raises(ValueError, match="already registered"):

                    @register_dispatch_task(config_cls=RegistryTestConfig)
                    class SecondTask(DispatchTask):
                        queue_cls = RegistryTestQueue

                        def execute(self, item, *, job=None, overrides=None):
                            return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS)

                        def build_job(self, item, *, overrides=None, ready_at=None, config=None):
                            return TestPumpQueue._job(task_key=dup_key)

                # Same class re-registration is idempotent (e.g. module reload).
                assert register_dispatch_task(config_cls=RegistryTestConfig)(FirstTask) is FirstTask
            finally:
                DISPATCH_REGISTRY.pop(dup_key, None)


class TestQueueBootstrap:
    def test_installed_apps_expose_dispatch_queue_modules(self):
        from backend.db_periodic_task.dispatch_queues import DummyTaskQueue
        from backend.dbm_aiagent.dispatch_queues import AITaskQueue

        assert DummyTaskQueue.namespace == "dummy"
        assert AITaskQueue.namespace == "ai"

    def test_ensure_queues_loaded_autodiscovers_once(self):
        import backend.db_periodic_task.dispatch.queue as queue_mod

        queue_mod._queues_discovered = False
        with patch("backend.db_periodic_task.dispatch.queue.autodiscover_modules") as mocked:
            DispatchQueue.ensure_queues_loaded()
            DispatchQueue.ensure_queues_loaded()
        mocked.assert_called_once_with("dispatch_queues")

    def test_queue_for_namespace_resolves_dummy_after_autodiscovery(self):
        import backend.db_periodic_task.dispatch.queue as queue_mod

        queue_mod._queues_discovered = False
        queue_cls = DispatchQueue.queue_for_namespace("dummy")
        assert queue_cls is not None
        assert queue_cls.namespace == "dummy"

    def test_duplicate_namespace_raises_at_definition(self):
        from typing import ClassVar

        ns = "dup-namespace-test"

        class DupConfigA(DispatchQueueConfig):
            namespace: ClassVar[str] = ns

        class DupQueueA(DispatchQueue):
            config_cls = DupConfigA

        assert DISPATCH_QUEUE_REGISTRY.get(ns) is DupQueueA

        class DupConfigB(DispatchQueueConfig):
            namespace: ClassVar[str] = ns

        try:
            with pytest.raises(DispatchQueueError):

                class DupQueueB(DispatchQueue):
                    config_cls = DupConfigB

        finally:
            DISPATCH_QUEUE_REGISTRY.pop(ns, None)

    def test_ephemeral_queue_never_evicts_real_queue_same_namespace(self):
        from typing import ClassVar

        ns = "ephemeral-collision-test"

        class RealConfig(DispatchQueueConfig):
            namespace: ClassVar[str] = ns

        class RealQueue(DispatchQueue):
            config_cls = RealConfig

        try:
            ephemeral = DispatchQueue.ephemeral_queue_for_namespace(ns)
            assert ephemeral.namespace == ns
            # The real queue must stay registered; defining the ephemeral
            # must not raise despite the namespace clash.
            assert DISPATCH_QUEUE_REGISTRY.get(ns) is RealQueue
        finally:
            DISPATCH_QUEUE_REGISTRY.pop(ns, None)
