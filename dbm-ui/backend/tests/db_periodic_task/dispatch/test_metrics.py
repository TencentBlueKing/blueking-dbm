import time
from unittest.mock import MagicMock, patch

import pytest

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.controller import AimdAction, PumpControlDecision, PumpController
from backend.db_periodic_task.dispatch.metrics import (
    HISTOGRAM_BUCKETS,
    TASK_METRICS_IDLE_TTL_SECONDS,
    TICK_RETENTION_SECONDS,
    DispatchMetrics,
)
from backend.db_periodic_task.dispatch.observability import DispatchStats, QueueDispatchReport


class TestDispatchMetrics:
    def test_queue_event_updates_cumulative_and_aimd_tick(self):
        script = MagicMock()
        with patch.object(DispatchMetrics, "_get_queue_event_script", return_value=script), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=MagicMock(),
        ):
            DispatchMetrics.record_queue_event("ai", "published", 3, timestamp=120.0)

        assert script.call_args.kwargs["keys"] == [
            "dispatch:ai:metrics:cumulative:events",
            "dispatch:ai:metrics:tick:0",
            "dispatch:ai:metrics:cumulative:started_at",
        ]
        assert script.call_args.kwargs["args"] == [
            "published",
            3,
            "t:12:published",
            TICK_RETENTION_SECONDS,
            120.0,
        ]

    def test_non_aimd_event_has_no_tick_field(self):
        script = MagicMock()
        with patch.object(DispatchMetrics, "_get_queue_event_script", return_value=script), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=MagicMock(),
        ):
            DispatchMetrics.record_queue_event("ai", "pump_not_started", timestamp=3601.0)

        assert script.call_args.kwargs["args"][2] == ""

    def test_read_queue_events_fills_fixed_zero_series(self):
        client = MagicMock()
        client.hgetall.return_value = {"published": "2", "unknown": "9"}
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            events = DispatchMetrics.read_queue_events("ai")

        assert events["published"] == 2
        assert events["enqueue_deadline_expired"] == 0
        assert events["pump_not_started"] == 0
        assert "unknown" not in events

    def test_task_outcome_uses_cumulative_key_and_idle_ttl(self):
        script = MagicMock()
        with patch.object(DispatchMetrics, "_get_task_outcome_script", return_value=script), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=MagicMock(),
        ):
            DispatchMetrics.record_task_event("ai", "redis.check", "success", 2, timestamp=100.0)

        assert script.call_args.kwargs["keys"] == [
            "dispatch:ai:metrics:cumulative:task:redis.check",
            "dispatch:ai:metrics:cumulative:started_at",
        ]
        assert script.call_args.kwargs["args"] == ["success", 2, TASK_METRICS_IDLE_TTL_SECONDS, 100.0]

    def test_histogram_batch_updates_mutually_exclusive_bins_once(self):
        script = MagicMock()
        with patch.object(DispatchMetrics, "_get_histogram_script", return_value=script), patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            return_value=MagicMock(),
        ):
            DispatchMetrics.record_histogram_values(
                "ai",
                "queue_wait_seconds",
                [0.1, 0.2, 5.0, 5.1],
                timestamp=100.0,
            )

        script.assert_called_once()
        args = script.call_args.kwargs["args"]
        assert args[0:2] == ["queue_wait_seconds", 4]
        assert args[2] == pytest.approx(10.4)
        assert args[3:5] == [100.0, 4]
        # <=0.1, <=0.5, <=5 and <=10 are mutually exclusive Redis bins.
        assert args[5:] == [0, 1, 1, 1, 3, 1, 4, 1]

    def test_read_task_outcomes_filters_unknown_fields(self):
        raw = {"success": "2", "error": "1", "unknown": "9"}
        client = MagicMock()
        client.hgetall.return_value = raw
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            outcomes = DispatchMetrics.read_task_outcomes("ai", "task")

        assert outcomes["success"] == 2
        assert outcomes["error"] == 1
        assert outcomes["timeout"] == 0
        assert "unknown" not in outcomes

    def test_read_histograms_converts_disjoint_bins_to_cumulative_buckets(self):
        raw = {
            "execution_seconds:bin:0": "2",
            "execution_seconds:bin:1": "3",
            f"execution_seconds:bin:{len(HISTOGRAM_BUCKETS['execution_seconds']) - 1}": "1",
            "execution_seconds:count": "6",
            "execution_seconds:sum": "3.5",
        }
        client = MagicMock()
        client.hgetall.return_value = raw
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            summary = DispatchMetrics.read_histograms("ai")["execution_seconds"]

        assert summary.count == 6
        assert summary.sum == 3.5
        assert summary.buckets[0][1] == 2
        assert summary.buckets[1][1] == 5
        assert summary.buckets[-1] == ("+Inf", 6)

    def test_queue_tick_counts_hmgets_requested_tick_fields(self):
        """Point-read one tick via HMGET; neighbor slots must not leak."""

        def hmget(_key, fields):
            data = {
                "t:12:ready_peeked": "15",
                "t:12:published": "5",
                "t:12:blocked": "1",
                # Neighbor slots — must never be requested for tick 12.
                "t:1:ready_peeked": "99",
                "t:120:ready_peeked": "7",
                "t:13:published": "3",
            }
            return [data.get(field) for field in fields]

        client = MagicMock()
        client.hmget.side_effect = hmget
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client) as mocked:
            # tick_id 12 → timestamp 120 → slot 12
            counts = DispatchMetrics.queue_tick_counts(
                "ai",
                12,
                names=("ready_peeked", "published", "blocked", "missing"),
            )

        assert counts == {"ready_peeked": 15, "published": 5, "blocked": 1}
        assert mocked.return_value.hmget.call_args.args[1] == [
            "t:12:ready_peeked",
            "t:12:published",
            "t:12:blocked",
        ]


class TestPumpController:
    @staticmethod
    def _queue(*, reserved: int):
        queue = MagicMock()
        queue.namespace = "ai"
        queue.reserved_count.return_value = reserved
        return queue

    @staticmethod
    def _decide(queue, settings, *, state, previous, tick_id=123):
        client = MagicMock()
        client.hgetall.return_value = state
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client,), patch.object(
            DispatchMetrics,
            "queue_tick_counts",
            return_value=previous,
        ), patch.object(PumpController, "_persist"):
            return PumpController.decide(queue, settings, current_tick_id=tick_id)

    def test_cold_start_uses_ten_percent_of_configured_concurrency(self):
        queue = self._queue(reserved=25)
        settings = DispatchQueueConfig(max_reserved=200)
        decision = self._decide(queue, settings, state={}, previous={})

        assert decision.aimd_action == "cold_start"
        assert decision.congestion_window == 20
        assert decision.effective_budget == 20
        assert decision.available_slots == 175

    def test_warm_decrease_multi_tick_halves_geometrically_then_recovers(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "200", "congestion_window": "200"}

        # Sustained congestion halves cwnd every tick: 200 -> 100 -> 50.
        for tick, expected_cwnd in ((123, 100), (124, 50)):
            previous = {"ready_peeked": 500, "published": int(state["effective_budget"]), "congestion": 1}
            decision = self._decide(queue, settings, state=state, previous=previous, tick_id=tick)
            assert decision.aimd_action == "decrease"
            assert decision.congestion_window == expected_cwnd
            assert decision.effective_budget == expected_cwnd
            assert decision.previous_congestion == 1
            state = {
                "tick_id": str(tick),
                "effective_budget": str(decision.effective_budget),
                "congestion_window": str(decision.congestion_window),
            }

        # Congestion clears with the reduced window still saturated: additive
        # increase resumes from 50 by one step (max_reserved // 20 = 10).
        previous = {"ready_peeked": 500, "published": 50}
        decision = self._decide(queue, settings, state=state, previous=previous, tick_id=125)
        assert decision.aimd_action == "increase"
        assert decision.congestion_window == 60

    def test_warm_decrease_floors_at_one(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "1", "congestion_window": "1"}
        previous = {"ready_peeked": 10, "published": 1, "congestion": 1}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.aimd_action == "decrease"
        assert decision.congestion_window == 1

    def test_blocked_and_publish_failed_do_not_trigger_md(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "50", "congestion_window": "50"}
        previous = {"ready_peeked": 100, "published": 50, "blocked": 3, "publish_failed": 1}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.aimd_action == "increase"
        assert decision.congestion_window == 60
        assert decision.effective_budget == 60

    def test_warm_hold_when_free_slots_limited_previous_tick(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        # previous effective budget was clamped by free slots, not cwnd
        state = {"tick_id": "122", "effective_budget": "20", "congestion_window": "50"}
        previous = {"ready_peeked": 100, "published": 20}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.aimd_action == "hold"
        assert decision.congestion_window == 50
        assert decision.effective_budget == 50

    def test_temporary_slot_shrink_does_not_poison_cwnd(self):
        queue = self._queue(reserved=190)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "50", "congestion_window": "50"}
        previous = {"ready_peeked": 100, "published": 50}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.available_slots == 10
        assert decision.congestion_window == 60
        assert decision.effective_budget == 10

    def test_warm_hold_when_demand_not_saturated(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "50", "congestion_window": "50"}
        previous = {"ready_peeked": 20, "published": 20}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.aimd_action == "hold"
        assert decision.effective_budget == 50
        assert decision.congestion_window == 50

    def test_concurrency_is_always_a_hard_ceiling(self):
        queue = self._queue(reserved=198)
        settings = DispatchQueueConfig(max_reserved=200)
        decision = self._decide(queue, settings, state={}, previous={})

        assert decision.available_slots == 2
        assert decision.congestion_window == 20
        assert decision.effective_budget == 2
        assert decision.effective_budget <= decision.available_slots

    def test_congestion_window_does_not_grow_past_concurrency(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        state = {"tick_id": "122", "effective_budget": "195", "congestion_window": "195"}
        previous = {"ready_peeked": 200, "published": 195}
        decision = self._decide(queue, settings, state=state, previous=previous)

        assert decision.aimd_action == "increase"
        assert decision.congestion_window == 200
        assert decision.effective_budget == 200

    def test_metrics_failure_falls_back_to_aimd_cold_start(self):
        queue = self._queue(reserved=0)
        settings = DispatchQueueConfig(max_reserved=200)
        with patch(
            "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
            side_effect=RuntimeError("redis down"),
        ), patch.object(PumpController, "_persist"):
            decision = PumpController.decide(queue, settings, current_tick_id=123)

        assert decision.congestion_window == 20
        assert decision.effective_budget == 20
        assert decision.aimd_action == "cold_start"
        assert decision.reserved_count_unknown is True

    def test_controller_state_serializes_booleans_and_reads_typed_values(self):
        pipeline = MagicMock()
        client = MagicMock()
        client.pipeline.return_value = pipeline
        decision = PumpControlDecision(
            namespace="ai",
            tick_id=123,
            effective_budget=50,
            congestion_window=50,
            available_slots=150,
            previous_congestion=1,
            aimd_action=AimdAction.DECREASE,
            reserved_count_unknown=False,
        )
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=client):
            PumpController._persist(decision)

        pipeline.hset.assert_called_once()
        mapping = pipeline.hset.call_args.kwargs["mapping"]
        assert mapping["reserved_count_unknown"] == 0
        assert mapping["aimd_action"] == "decrease"
        assert all(not isinstance(value, bool) for value in mapping.values())
        pipeline.expire.assert_called_once()

        raw = {
            "tick_id": "123",
            "effective_budget": "50",
            "congestion_window": "50",
            "previous_congestion": "1",
            "aimd_action": "decrease",
            "reserved_count_unknown": "0",
            "updated_at": "1710000000.5",
        }
        read_client = MagicMock()
        read_client.hgetall.return_value = raw
        with patch("backend.db_periodic_task.dispatch.routing.conn_for_namespace", return_value=read_client):
            state = PumpController.read_state("ai")

        assert state["tick_id"] == 123
        assert state["congestion_window"] == 50
        assert state["previous_congestion"] == 1
        assert state["aimd_action"] == "decrease"
        assert state["reserved_count_unknown"] is False
        assert state["updated_at"] == 1710000000.5


class TestDispatchReports:
    def test_queue_report_explains_concurrency_ceiling(self):
        queue = MagicMock()
        queue.load_config.return_value = DispatchQueueConfig(max_reserved=200)
        queue.pending_count.return_value = 20
        queue.ready_count.return_value = 20
        queue.delayed_count.return_value = 0
        queue.reserved_count.return_value = 10
        with patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.queue_for_namespace",
            return_value=queue,
        ), patch(
            "backend.db_periodic_task.dispatch.pump.inspect_queue_pump_lock",
            return_value={"state": "free"},
        ), patch.object(
            DispatchMetrics,
            "read_queue_events",
            return_value={"published": 100},
        ), patch.object(
            DispatchMetrics,
            "read_histograms",
            return_value={},
        ), patch.object(
            DispatchMetrics,
            "read_started_at",
            return_value=1000.0,
        ), patch.object(
            DispatchMetrics,
            "queue_tick_counts",
            return_value={"ready_peeked": 5, "published": 5},
        ), patch.object(
            PumpController,
            "read_state",
            return_value={"effective_budget": "100", "available_slots": "190"},
        ):
            report = DispatchStats.queue_report("ai")

        assert report.partial is False
        assert report.tick_seconds == 10
        assert report.last_tick_counts == {"ready_peeked": 5, "published": 5}
        assert report.events == {"published": 100}
        assert report.diagnosis == ["healthy"]
        assert "budget=100" in report.format_summary()
        assert "last_tick=" in report.format_summary()

    def test_queue_dashboard_shows_paused_pump(self):
        queue = MagicMock()
        queue.load_config.return_value = DispatchQueueConfig(max_reserved=50)
        queue.pending_count.return_value = 20
        queue.ready_count.return_value = 20
        queue.delayed_count.return_value = 0
        queue.reserved_count.return_value = 0
        with patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.queue_for_namespace",
            return_value=queue,
        ), patch(
            "backend.db_periodic_task.dispatch.pump.inspect_queue_pump_lock",
            return_value={
                "state": "paused",
                "held": True,
                "owner": "dispatch:paused",
                "ttl_seconds": 90,
            },
        ), patch.object(
            DispatchMetrics, "read_queue_events", return_value={}
        ), patch.object(
            DispatchMetrics,
            "read_histograms",
            return_value={},
        ), patch.object(
            DispatchMetrics,
            "read_started_at",
            return_value=1000.0,
        ), patch.object(
            DispatchMetrics,
            "queue_tick_counts",
            return_value={},
        ), patch.object(
            PumpController,
            "read_state",
            return_value={"effective_budget": "5", "available_slots": "50"},
        ):
            report = DispatchStats.queue_report("dummy")

        assert report.pump_lock["state"] == "paused"
        assert report.diagnosis == ["pump_paused"]
        assert "pump=paused" in report.format_summary()
        dashboard = report.format_dashboard()
        assert "status=PAUSED" in dashboard
        assert "pump=paused(90s)" in dashboard
        assert "diagnosis  pump_paused" in dashboard

    def test_queue_dashboard_renders_bars_and_last_tick(self):
        report = QueueDispatchReport(
            namespace="ai",
            timestamp=1710000000.0,
            tick_seconds=10,
            pending_total=12,
            pending_ready=10,
            pending_delayed=2,
            reserved=40,
            config={
                "max_reserved": 200,
                "max_admitted_jobs": 2000,
            },
            controller={
                "effective_budget": 15,
                "available_slots": 160,
                "congestion_window": 15,
                "aimd_action": "increase",
                "tick_id": "123",
            },
            events={"published": 100, "worker_finished": 80},
            histograms={},
            metrics_started_at=1709990000.0,
            diagnosis=["healthy"],
            last_tick_id=123,
            last_tick_counts={"ready_peeked": 20, "published": 15, "blocked": 0, "reserved": 15},
        )
        dashboard = report.format_dashboard()
        assert "dispatch[ai]" in dashboard
        assert "status=HEALTHY" in dashboard
        assert "generation=" in dashboard
        assert "reserved" in dashboard and "[#" in dashboard
        assert "aimd=increase" in dashboard
        assert "ready=20" in dashboard
        assert "sent=15" in dashboard
        assert "#123" in dashboard
        assert time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(123 * 10)) in dashboard
        assert time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(1710000000.0)) in dashboard
        assert "52/2000" in dashboard  # pending + reserved admission occupancy
        assert "free=" in dashboard
        assert "generation flow" in dashboard
        assert "generation issues" in dashboard
        assert "latency(s)" not in dashboard

    def test_watch_queue_prints_frames(self):
        from io import StringIO

        frames = [
            QueueDispatchReport(
                namespace="ai",
                timestamp=1.0,
                tick_seconds=10,
                pending_total=1,
                pending_ready=1,
                pending_delayed=0,
                reserved=0,
                config={"max_reserved": 3},
                controller={"effective_budget": 1, "aimd_action": "hold"},
                events={},
                histograms={},
                metrics_started_at=1.0,
                diagnosis=["healthy"],
                last_tick_id=1,
                last_tick_counts={"ready_peeked": 1, "published": 1},
            ),
            QueueDispatchReport(
                namespace="ai",
                timestamp=2.0,
                tick_seconds=10,
                pending_total=0,
                pending_ready=0,
                pending_delayed=0,
                reserved=1,
                config={"max_reserved": 3},
                controller={"effective_budget": 2, "aimd_action": "increase"},
                events={},
                histograms={},
                metrics_started_at=1.0,
                diagnosis=["healthy"],
                last_tick_id=2,
                last_tick_counts={"ready_peeked": 2, "published": 1},
            ),
        ]
        stream = StringIO()
        with patch.object(DispatchStats, "queue_report", side_effect=frames), patch(
            "backend.db_periodic_task.dispatch.observability.time.sleep"
        ):
            DispatchStats.watch_queue("ai", ticks=2, interval_seconds=0, clear=False, stream=stream)

        output = stream.getvalue()
        assert output.count("dispatch[ai]") == 2
        assert "aimd=hold" in output
        assert "aimd=increase" in output

    def test_task_report_reads_current_generation_outcomes(self):
        outcomes = {"success": 3, "error": 1}
        queue_cls = MagicMock()
        queue_cls.task_counts.return_value = (7, 2)
        with patch.object(DispatchMetrics, "read_task_outcomes", return_value=outcomes), patch.object(
            DispatchMetrics,
            "read_started_at",
            return_value=1000.0,
        ), patch.object(DispatchStats, "_load_registered", return_value={"redis.check": {"namespace": "ai"}},), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.queue_for_namespace",
            return_value=queue_cls,
        ):
            report = DispatchStats.task_report("redis.check")

        assert report.outcomes == {"success": 3, "error": 1}
        assert report.pending == 7
        assert report.reserved == 2
        assert report.admitted == 9
        assert report.partial is False
        assert "pending=7 reserved=2 admitted=9" in report.format_summary()

    def test_snapshot_reuses_registry_without_loading_task_counts(self):
        registered = {"task.a": {"namespace": "ai"}, "task.b": {"namespace": "ai"}}
        with patch.object(DispatchStats, "_load_registered", return_value=registered), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.registered_queues",
            return_value=[],
        ), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.aggregate_pending_count",
            return_value=0,
        ), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.aggregate_ready_count",
            return_value=0,
        ), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.aggregate_delayed_count",
            return_value=0,
        ), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.aggregate_reserved_count",
            return_value=0,
        ), patch.object(
            DispatchStats,
            "_load_pump_config",
            return_value={},
        ), patch.object(
            DispatchMetrics,
            "read_task_outcomes",
            side_effect=[
                {"success": 2},
                {"error": 1},
            ],
        ) as read_outcomes, patch.object(
            DispatchStats, "task_report"
        ) as task_report:
            snapshot = DispatchStats.snapshot()

        assert [(item.task_key, item.outcomes) for item in snapshot.task_reports] == [
            ("task.a", {"success": 2}),
            ("task.b", {"error": 1}),
        ]
        assert read_outcomes.call_count == 2
        task_report.assert_not_called()

    def test_task_report_is_partial_when_live_admitted_is_unavailable(self):
        with patch.object(DispatchMetrics, "read_task_outcomes", return_value={}), patch.object(
            DispatchMetrics,
            "read_started_at",
            return_value=None,
        ), patch.object(
            DispatchStats,
            "_load_registered",
            return_value={"redis.check": {"namespace": "missing"}},
        ), patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.queue_for_namespace",
            return_value=None,
        ):
            report = DispatchStats.task_report("redis.check")

        assert report.pending == -1
        assert report.reserved == -1
        assert report.admitted == -1
        assert report.partial is True

    def test_unregistered_queue_returns_partial_report(self):
        with patch(
            "backend.db_periodic_task.dispatch.observability.DispatchQueue.queue_for_namespace",
            return_value=None,
        ):
            report = DispatchStats.queue_report("missing")

        assert report.partial is True
        assert report.diagnosis == ["unregistered_queue"]

    def test_dashboard_shows_relative_decide_tick_delta(self):
        base = dict(
            namespace="dummy",
            timestamp=1710000000.0,
            tick_seconds=10,
            pending_total=1,
            pending_ready=1,
            pending_delayed=0,
            reserved=0,
            config={"max_reserved": 50, "max_admitted_jobs": 2000},
            events={},
            histograms={},
            metrics_started_at=1000.0,
            pump_lock={"state": "free"},
            last_tick_counts={},
        )
        ahead = QueueDispatchReport(
            **base,
            controller={"tick_id": 125, "effective_budget": 1, "aimd_action": "hold"},
            diagnosis=["healthy"],
            last_tick_id=124,
        )
        aligned = QueueDispatchReport(
            **base,
            controller={"tick_id": 124, "effective_budget": 1, "aimd_action": "hold"},
            diagnosis=["healthy"],
            last_tick_id=124,
        )
        behind = QueueDispatchReport(
            **base,
            controller={"tick_id": 122, "effective_budget": 1, "aimd_action": "hold"},
            diagnosis=["pump_delayed"],
            last_tick_id=124,
        )

        assert "decide=#125 (last=#124, Δ+1 tick)" in ahead.format_dashboard()
        assert "decide=#124 (last=#124, Δ0 tick)" in aligned.format_dashboard()
        delayed = behind.format_dashboard()
        assert "decide=#122 (last=#124, Δ-2 tick)" in delayed
        assert "status=WARN" in delayed
        assert "diagnosis  pump_delayed" in delayed

    def test_diagnose_marks_pump_delayed_and_last_tick_failures(self):
        delayed = QueueDispatchReport(
            namespace="dummy",
            timestamp=1.0,
            tick_seconds=10,
            pending_total=5,
            pending_ready=5,
            pending_delayed=0,
            reserved=0,
            config={"max_reserved": 50},
            controller={"tick_id": 10},
            events={"pump_ticks_skipped": 3, "pump_lock_contention": 1},
            histograms={},
            metrics_started_at=1000.0,
            pump_lock={"state": "free"},
            last_tick_id=12,
            last_tick_counts={"blocked": 3, "publish_failed": 1},
        )
        assert DispatchStats._diagnose(delayed) == [
            "pump_delayed",
            "broker_publish_failures",
            "reservation_blocked",
        ]

        paused = QueueDispatchReport(
            namespace="dummy",
            timestamp=1.0,
            tick_seconds=10,
            pending_total=5,
            pending_ready=5,
            pending_delayed=0,
            reserved=0,
            config={"max_reserved": 50},
            controller={"tick_id": 10},
            events={},
            histograms={},
            metrics_started_at=1000.0,
            pump_lock={"state": "paused", "ttl_seconds": -1},
            last_tick_id=12,
        )
        assert DispatchStats._diagnose(paused) == ["pump_paused"]
        assert "skipped=" in delayed.format_dashboard()
        assert "lock_contend=" in delayed.format_dashboard()
