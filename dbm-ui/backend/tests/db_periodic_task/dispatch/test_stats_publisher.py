import importlib
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_periodic_task.dispatch.metrics import HistogramSummary
from backend.db_periodic_task.dispatch.observability import DispatchStats, QueueDispatchReport, TaskDispatchReport


@pytest.fixture(scope="module")
def sp(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.dispatch.stats_publisher")


def _make_queue_report(ns="ai", **overrides):
    base = dict(
        namespace=ns,
        timestamp=time.time(),
        tick_seconds=10,
        pending_total=10,
        pending_ready=5,
        pending_delayed=3,
        reserved=2,
        config={"max_admitted_jobs": 100, "max_reserved": 20},
        controller={"effective_budget": 15, "available_slots": 10, "congestion_window": 8},
        events={"enqueued": 100, "published": 80},
        histograms={
            "execution_seconds": HistogramSummary(
                buckets=[("1", 5), ("+Inf", 8)],
                count=8,
                sum=12.5,
            )
        },
        metrics_started_at=1000.0,
        pump_lock={"state": "free"},
        producer_gate={"state": "free"},
        diagnosis=["healthy"],
        partial=False,
        last_tick_id=0,
        last_tick_counts={},
    )
    base.update(overrides)
    return QueueDispatchReport(**base)


def _make_task_report(task_key="ai.task", ns="ai", **overrides):
    base = dict(
        task_key=task_key,
        namespace=ns,
        timestamp=time.time(),
        pending=2,
        reserved=1,
        admitted=3,
        outcomes={"success": 30, "error": 1},
        metrics_started_at=1000.0,
        partial=False,
    )
    base.update(overrides)
    return TaskDispatchReport(**base)


def _make_snapshot(queues=None, tasks=None, timestamp=None):
    return SimpleNamespace(
        timestamp=timestamp or time.time(),
        queues=queues or [_make_queue_report()],
        task_reports=tasks or [_make_task_report()],
    )


def _latest_written(client, key):
    calls = [call for call in client.set.call_args_list if call[0][0] == key]
    assert calls, f"publisher never wrote {key}"
    return json.loads(calls[-1][0][1])


class TestStatsPublisher:
    def test_publish_writes_schema_v2_cumulative_payload(self, sp):
        client = MagicMock()
        client.set.return_value = True
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
            return_value=_make_snapshot(),
        ):
            sp.publish_dispatch_stats()

        payload = _latest_written(client, sp.KEY_LATEST)
        assert payload["schema_version"] == 2
        assert payload["generated_at"]
        assert payload["queues"][0]["events"]["enqueued"] == 100
        assert payload["queues"][0]["histograms"]["execution_seconds"]["buckets"][-1] == ["+Inf", 8]
        assert payload["queues"][0]["metrics_started_at"] == 1000.0
        assert payload["tasks"][0]["outcomes"] == {"success": 30, "error": 1}
        assert "windows" not in payload
        assert "samples" not in json.dumps(payload)

    def test_heartbeat_updated_after_lock_acquire(self, sp):
        client = MagicMock()
        client.set.return_value = True
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
            return_value=_make_snapshot(),
        ):
            sp.publish_dispatch_stats()
        heartbeat_calls = [call for call in client.set.call_args_list if call[0][0] == sp.KEY_HEARTBEAT]
        assert heartbeat_calls
        float(heartbeat_calls[-1][0][1])

    def test_publish_skips_when_lock_held_by_another_owner(self, sp):
        client = MagicMock()
        client.set.return_value = False
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
        ) as snapshot:
            sp.publish_dispatch_stats()
        snapshot.assert_not_called()

    def test_lock_uses_owner_value_and_ttl(self, sp):
        client = MagicMock()
        client.set.return_value = True
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
            return_value=_make_snapshot(),
        ):
            sp.publish_dispatch_stats()
        lock_call = next(call for call in client.set.call_args_list if call[0][0] == sp.KEY_PUBLISHER_LOCK)
        assert lock_call[0][1].startswith("stats_publisher:")
        assert lock_call.kwargs == {"nx": True, "ex": 60}

    def test_snapshot_failure_leaves_cache_untouched(self, sp):
        client = MagicMock()
        client.set.return_value = True
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
            side_effect=RuntimeError("redis boom"),
        ):
            sp.publish_dispatch_stats()
        assert not [call for call in client.set.call_args_list if call[0][0] == sp.KEY_LATEST]

    def test_task_cap_truncates_and_marks_namespace_partial(self, sp):
        tasks = [_make_task_report(task_key=f"t{index}") for index in range(sp.MAX_TASK_EXPORTS + 10)]
        payload = sp.build_payload(_make_snapshot(tasks=tasks))
        assert len(payload["tasks"]) == sp.MAX_TASK_EXPORTS
        assert payload["queues"][0]["partial"] == 1

    def test_partial_task_marks_owning_namespace_partial(self, sp):
        payload = sp.build_payload(_make_snapshot(tasks=[_make_task_report(partial=True)]))
        assert payload["queues"][0]["partial"] == 1
        assert payload["tasks"][0]["partial"] == 1

    def test_unavailable_values_become_null(self, sp):
        queue = _make_queue_report(pending_total=-1, reserved=-1, config={})
        payload = sp.build_payload(_make_snapshot(queues=[queue]))
        assert payload["queues"][0]["pending"] is None
        assert payload["queues"][0]["reserved"] is None
        assert payload["queues"][0]["max_admitted_jobs"] is None

    def test_missed_publish_is_caught_up_by_next_snapshot(self, sp):
        first = sp.build_payload(_make_snapshot(queues=[_make_queue_report(events={"published": 10})]))
        after_gap = sp.build_payload(_make_snapshot(queues=[_make_queue_report(events={"published": 17})]))
        assert first["queues"][0]["events"]["published"] == 10
        assert after_gap["queues"][0]["events"]["published"] == 17

    def test_payload_size_warning(self, sp, caplog):
        client = MagicMock()
        client.set.return_value = True
        with patch("backend.db_periodic_task.dispatch.routing.global_conn", return_value=client), patch.object(
            DispatchStats,
            "snapshot",
            return_value=_make_snapshot(),
        ), patch.object(sp, "PAYLOAD_WARN_BYTES", 1):
            sp.publish_dispatch_stats()
        assert "exceeds" in caplog.text

    def test_periodic_task_registered(self, sp):
        assert callable(sp.dispatch_publish_stats)
