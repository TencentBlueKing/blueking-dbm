import fnmatch
import importlib
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.reservation import ReservationStatus
from backend.db_periodic_task.models import DispatchQueueRoute


@pytest.fixture(autouse=True)
@pytest.mark.django_db
def clean_route_table():
    DispatchQueueRoute.objects.all().delete()
    yield
    DispatchQueueRoute.objects.all().delete()


@pytest.fixture(scope="module")
def remap_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.dispatch.remap")


@pytest.fixture(scope="module")
def pump_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.dispatch.pump")


class _FakeScanClient:
    def __init__(self, keys):
        self.keys = list(keys)
        self.unlinked = []

    def scan_iter(self, match, count=500):
        for key in self.keys:
            if fnmatch.fnmatchcase(key, match):
                yield key

    def unlink(self, *keys):
        self.unlinked.extend(keys)


def test_sweep_namespace_clears_only_its_own_namespace(remap_module):
    client = _FakeScanClient(
        [
            "dispatch:ns:pending",
            "dispatch:ns:job:a",
            "dispatch:other:pending",
            "dispatch:registered",
        ]
    )
    with patch("backend.db_periodic_task.dispatch.routing.conn_for_alias", return_value=client):
        result = remap_module.sweep_namespace("dispatch_0", "ns", dry_run=False)

    assert result["deleted"] == 2
    assert result["matched"] == 2
    assert client.unlinked == ["dispatch:ns:pending", "dispatch:ns:job:a"]


def test_sweep_namespace_dry_run_counts_without_deleting(remap_module):
    client = _FakeScanClient(["dispatch:ns:pending", "dispatch:ns:job:a"])
    with patch("backend.db_periodic_task.dispatch.routing.conn_for_alias", return_value=client):
        result = remap_module.sweep_namespace("dispatch_0", "ns", dry_run=True)

    assert result["matched"] == 2
    assert result["deleted"] == 0
    assert client.unlinked == []


@pytest.mark.django_db
def test_remap_order_pause_save_wait_sweep_wait_sweep_no_resume(remap_module):
    with override_settings(DISPATCH_REDIS_ALIASES=["dispatch_0", "dispatch_1"]):
        DispatchQueueRoute.objects.create(
            namespace="ns",
            redis_alias="dispatch_0",
            creator="tester",
            updater="tester",
        )
        order = []
        saved_instances = []
        real_save = DispatchQueueRoute.save

        def save_spy(instance, *args, **kwargs):
            saved_instances.append(instance)
            return real_save(instance, *args, **kwargs)

        with patch.object(
            remap_module, "pause_queue_pump", side_effect=lambda *args, **kwargs: order.append("pause")
        ) as pause, patch.object(
            remap_module, "_wait_convergence_window", side_effect=lambda: order.append("wait")
        ) as wait, patch.object(
            remap_module,
            "sweep_namespace",
            side_effect=lambda *args, **kwargs: order.append("sweep") or {"matched": 0, "deleted": 0, "batches": 0},
        ) as sweep, patch.object(
            DispatchQueueRoute, "save", new=save_spy
        ):
            result = remap_module.remap_namespace("ns", "dispatch_1", mode="drop", dry_run=False)

        assert order == ["pause", "wait", "sweep", "wait", "sweep"]
        assert wait.call_count == 2
        assert sweep.call_count == 2
        pause.assert_called_once_with("ns", seconds=None, alias="dispatch_0")
        assert len(saved_instances) == 1
        assert saved_instances[0].namespace == "ns"
        assert result["convergence_window_seconds"] == 90
        assert DispatchQueueRoute.objects.get(namespace="ns").redis_alias == "dispatch_1"


@pytest.mark.django_db
def test_remap_mutation_runs_full_clean_and_never_queryset_update(remap_module):
    with override_settings(DISPATCH_REDIS_ALIASES=["dispatch_0", "dispatch_1"]):
        DispatchQueueRoute.objects.create(
            namespace="ns",
            redis_alias="dispatch_0",
            creator="tester",
            updater="tester",
        )
        with patch.object(remap_module, "pause_queue_pump"), patch.object(
            remap_module, "_wait_convergence_window"
        ), patch.object(
            remap_module, "sweep_namespace", return_value={"matched": 0, "deleted": 0, "batches": 0}
        ), patch.object(
            DispatchQueueRoute, "full_clean"
        ) as full_clean, patch.object(
            DispatchQueueRoute.objects, "update"
        ) as queryset_update:
            remap_module.remap_namespace("ns", "dispatch_1", dry_run=False)

        full_clean.assert_called_once()
        queryset_update.assert_not_called()


@pytest.mark.django_db
def test_remap_second_sweep_warns_on_late_keys(remap_module, caplog):
    with override_settings(DISPATCH_REDIS_ALIASES=["dispatch_0", "dispatch_1"]):
        DispatchQueueRoute.objects.create(
            namespace="ns",
            redis_alias="dispatch_0",
            creator="tester",
            updater="tester",
        )
        sweeps = [
            {"matched": 0, "deleted": 0, "batches": 0},
            {"matched": 3, "deleted": 3, "batches": 1},
        ]
        with patch.object(remap_module, "pause_queue_pump"), patch.object(
            remap_module, "_wait_convergence_window"
        ), patch.object(remap_module, "sweep_namespace", side_effect=sweeps), caplog.at_level("ERROR", logger="root"):
            remap_module.remap_namespace("ns", "dispatch_1", dry_run=False)

    assert "late keys" in caplog.text
    assert "second convergence window" in caplog.text


def test_pause_queue_pump_pinned_alias_uses_pool_client():
    from backend.db_periodic_task.dispatch import pump as pump_module

    client = MagicMock()
    with patch("backend.db_periodic_task.dispatch.routing.conn_for_alias", return_value=client), patch(
        "backend.db_periodic_task.dispatch.routing.conn_for_namespace",
        side_effect=AssertionError("remap must pin the old alias explicitly"),
    ):
        info = pump_module.pause_queue_pump("ns", seconds=None, alias="dispatch_1")

    assert info == {"namespace": "ns", "paused": True, "ttl_seconds": None}
    client.set.assert_any_call("dispatch:ns:pump_lock", pump_module.PUMP_PAUSE_OWNER)


def test_fetch_job_fanout_finds_payload_across_candidates():
    from backend.db_periodic_task.dispatch.base import DispatchTask

    job = DispatchJob(
        job_id="ghost.task:item",
        task_key="ghost.task",
        namespace="ghost",
        work_item_id="item",
    )
    ai_queue = MagicMock()
    ai_queue.get_job.return_value = None
    ghost_queue = MagicMock()
    ghost_queue.get_job.return_value = job
    with patch("backend.db_periodic_task.dispatch.base.namespace_for_job_id", return_value=""), patch(
        "backend.db_periodic_task.dispatch.base.candidate_namespaces",
        return_value={"ai", "ghost"},
    ), patch(
        "backend.db_periodic_task.dispatch.queue.DispatchQueue.queue_for_namespace",
        side_effect=lambda ns: None,
    ), patch(
        "backend.db_periodic_task.dispatch.queue.DispatchQueue.ephemeral_queue_for_namespace",
        side_effect=lambda ns: {"ai": ai_queue, "ghost": ghost_queue}[ns],
    ):
        assert DispatchTask.fetch_job("ghost.task:item") is job

    ai_queue.get_job.assert_called_once_with("ghost.task:item")
    ghost_queue.get_job.assert_called_once_with("ghost.task:item")


def test_execute_job_unknown_task_cleans_up_via_job_namespace():
    from backend.db_periodic_task.dispatch.base import DispatchTask
    from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

    job = DispatchJob(
        job_id="ghost.task:item",
        task_key="ghost.task",
        namespace="ghost",
        work_item_id="item",
    )
    ghost_queue = MagicMock()
    with patch.object(DispatchTask, "fetch_job", return_value=job), patch.dict(
        DISPATCH_REGISTRY, {}, clear=True
    ), patch("backend.db_periodic_task.dispatch.queue.DispatchQueue.queue_for_namespace", return_value=None,), patch(
        "backend.db_periodic_task.dispatch.queue.DispatchQueue.ephemeral_queue_for_namespace",
        return_value=ghost_queue,
    ), patch(
        "backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job"
    ) as finalize:
        DispatchTask.execute_job("ghost.task:item")

    ghost_queue.record_outcome.assert_called_once_with("ghost.task", DispatchOutcomeType.ERROR)
    finalize.assert_called_once_with(
        queue_cls=ghost_queue,
        job_id="ghost.task:item",
        task_key="ghost.task",
        work_item_id="item",
    )


def test_execute_job_missing_payload_unregistered_is_idempotent_noop():
    from backend.db_periodic_task.dispatch.base import DispatchTask

    with patch.object(DispatchTask, "fetch_job", return_value=None), patch(
        "backend.db_periodic_task.dispatch.base.namespace_for_job_id",
        return_value="",
    ), patch.object(DispatchTask, "discard_orphaned_job") as discard, patch(
        "backend.db_periodic_task.dispatch.lifecycle.QueueLifecycle.finalize_job"
    ) as finalize:
        DispatchTask.execute_job("ghost.task:item")

    discard.assert_not_called()
    finalize.assert_not_called()


def test_pump_publishes_wire_format_args_job_id_only(pump_module):
    job = DispatchJob(
        job_id="task:item",
        task_key="task",
        namespace="test",
        work_item_id="item",
    )
    queue = MagicMock()
    queue.ns.return_value = "test"
    queue.resolve_reserved_record_ttl_from_job.return_value = 60
    with patch.object(
        pump_module.QueueReservation,
        "reserve_jobs",
        return_value=[ReservationStatus.RESERVED],
    ), patch("backend.db_periodic_task.dispatch.pump.dispatch_execute_job.apply_async") as apply_async:
        stats = pump_module._PumpTickStats()
        pump_module._reserve_and_publish(
            queue,
            [job],
            DispatchQueueConfig(max_reserved=10),
            SimpleNamespace(effective_budget=10),
            time.monotonic() + 10,
            123,
            stats,
        )

    apply_async.assert_called_once_with(args=[job.job_id])
    assert stats.published == 1
