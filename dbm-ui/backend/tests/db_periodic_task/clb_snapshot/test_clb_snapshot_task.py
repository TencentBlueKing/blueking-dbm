import random
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_periodic_task.clb_snapshot import task as task_module
from backend.db_periodic_task.clb_snapshot.task import (
    CLB_SNAPSHOT_TASK_KEY,
    ClbSnapshotTask,
    ClbSnapshotTaskConfig,
    batch_work_item_id,
    snapshot_clusters,
    submit,
)
from backend.db_periodic_task.dispatch.nameservice_queue import NameserviceQueue
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY


def _detail(clb_id="lb-1", region="ap-test", listener_id="lbl-1"):
    return SimpleNamespace(clb_id=clb_id, clb_ip="1.1.1.9", listener_id=listener_id, clb_region=region)


def _entry(entry_id, cluster_id, detail=None):
    details = [detail] if detail is not None else []
    return SimpleNamespace(
        id=entry_id,
        cluster_id=cluster_id,
        entry=f"entry{entry_id}.example.db",
        clbentrydetail_set=SimpleNamespace(all=lambda: details),
    )


def _patch_entries(entries):
    qs = MagicMock()
    qs.prefetch_related.return_value = entries
    return patch.object(task_module.ClusterEntry.objects, "filter", return_value=qs)


def _rs_response(ips, code=0):
    return {"code": code, "data": {"ips": ips}, "message": "err" if code else ""}


@pytest.fixture(autouse=True)
def no_gate_sleep():
    with patch.object(task_module, "NAMESERVICE_CALL_GATE") as gate:
        yield gate


@pytest.fixture
def api():
    with patch.object(task_module, "NameServiceApi") as mocked:
        yield mocked


@pytest.fixture
def health():
    with patch.object(task_module.CLBManage, "describe_target_health") as mocked:
        yield mocked


# ---------------------------------------------------------------- registration


def test_task_registered_on_nameservice_queue():
    assert DISPATCH_REGISTRY[CLB_SNAPSHOT_TASK_KEY] is ClbSnapshotTask
    assert ClbSnapshotTask.queue_cls is NameserviceQueue
    assert ClbSnapshotTask.namespace == "nameservice"


def test_task_config_defaults():
    config = ClbSnapshotTaskConfig()
    assert config.enabled is True
    assert config.execution_timeout_seconds == 300
    assert config.queue_wait_ttl_seconds == 6 * 3600


def test_work_item_id_ignores_order():
    ids = list(range(1, 51))
    shuffled = ids[:]
    random.shuffle(shuffled)
    assert batch_work_item_id(ids) == batch_work_item_id(shuffled)
    assert batch_work_item_id(ids).startswith("clb:")
    assert batch_work_item_id(ids) != batch_work_item_id(ids[:-1])


# ---------------------------------------------------------------- execute


def test_unhealthy_rs_is_listener_intersection(api, health):
    api.clb_get_target_private_ips.return_value = _rs_response(["2.2.2.2:30000", "1.1.1.1:30000"])
    health.return_value = {"abnormalips": ["1.1.1.1:30000", "3.3.3.3:30000"]}
    with _patch_entries([_entry(11, 1, _detail())]):
        [snap] = snapshot_clusters([1])

    entry = snap.entries[0]
    assert entry.listener_rs == ["1.1.1.1:30000", "2.2.2.2:30000"]
    assert entry.unhealthy_rs == ["1.1.1.1:30000"]
    assert entry.listener_rs_error is None and entry.health_error is None
    assert (entry.clb_id, entry.listener_id, entry.region) == ("lb-1", "lbl-1", "ap-test")


@pytest.mark.parametrize("response", [_rs_response([], code=1), RuntimeError("down")])
def test_listener_rs_failure_is_unknown_not_empty(api, health, response):
    if isinstance(response, Exception):
        api.clb_get_target_private_ips.side_effect = response
    else:
        api.clb_get_target_private_ips.return_value = response
    health.return_value = {"abnormalips": ["1.1.1.1:30000"]}
    with _patch_entries([_entry(11, 1, _detail())]):
        [snap] = snapshot_clusters([1])

    entry = snap.entries[0]
    assert entry.listener_rs is None
    assert entry.unhealthy_rs is None
    assert entry.listener_rs_error


@pytest.mark.parametrize("response", [RuntimeError("boom"), {}, {"abnormalips": "bad"}])
def test_health_failure_is_unknown(api, health, response):
    api.clb_get_target_private_ips.return_value = _rs_response(["1.1.1.1:30000"])
    if isinstance(response, Exception):
        health.side_effect = response
    else:
        health.return_value = response
    with _patch_entries([_entry(11, 1, _detail())]):
        [snap] = snapshot_clusters([1])

    entry = snap.entries[0]
    assert entry.listener_rs == ["1.1.1.1:30000"]
    assert entry.unhealthy_rs is None
    assert entry.health_error


def test_null_abnormal_ips_means_healthy(api, health):
    api.clb_get_target_private_ips.return_value = _rs_response(["1.1.1.1:30000"])
    health.return_value = {"abnormalips": None, "abnormalcount": 0}
    with _patch_entries([_entry(11, 1, _detail())]):
        [snap] = snapshot_clusters([1])
    assert snap.entries[0].unhealthy_rs == []
    assert snap.entries[0].health_error is None


def test_health_reused_per_load_balancer(api, health):
    api.clb_get_target_private_ips.return_value = _rs_response(["1.1.1.1:30000"])
    health.return_value = {"abnormalips": []}
    entries = [
        _entry(11, 1, _detail(listener_id="lbl-1")),
        _entry(21, 2, _detail(listener_id="lbl-2")),
        _entry(31, 3, _detail(clb_id="lb-2")),
    ]
    with _patch_entries(entries):
        snapshot_clusters([1, 2, 3])
    assert health.call_count == 2
    assert api.clb_get_target_private_ips.call_count == 3


@pytest.mark.parametrize("detail", [_detail(clb_id=""), _detail(region=" "), None])
def test_incomplete_metadata_makes_no_calls(api, health, detail):
    with _patch_entries([_entry(11, 1, detail)]):
        [snap] = snapshot_clusters([1])
    assert snap.entries[0].meta_error
    assert not api.clb_get_target_private_ips.called
    assert not health.called


def test_every_call_goes_through_gate(api, health, no_gate_sleep):
    api.clb_get_target_private_ips.return_value = _rs_response(["1.1.1.1:30000"])
    health.return_value = {"abnormalips": []}
    with _patch_entries([_entry(11, 1, _detail())]):
        snapshot_clusters([1])
    assert no_gate_sleep.acquire.call_count == 2


def test_one_entry_failure_does_not_stop_batch(api, health):
    api.clb_get_target_private_ips.side_effect = [RuntimeError("down"), _rs_response(["2.2.2.2:30000"])]
    health.return_value = {"abnormalips": []}
    entries = [_entry(11, 1, _detail()), _entry(21, 2, _detail(clb_id="lb-2"))]
    with _patch_entries(entries):
        snaps = {s.cluster_id: s for s in snapshot_clusters([1, 2])}
    assert snaps[1].entries[0].listener_rs is None
    assert snaps[2].entries[0].listener_rs == ["2.2.2.2:30000"]


def test_unexpected_entry_error_is_recorded(api, health):
    with _patch_entries([_entry(11, 1, _detail())]), patch.object(
        task_module, "_snapshot_entry", side_effect=[ValueError("bad")]
    ):
        [snap] = snapshot_clusters([1])
    assert "bad" in snap.entries[0].meta_error


def test_cluster_without_clb_entry_gets_empty_snapshot(api, health):
    with _patch_entries([]):
        [snap] = snapshot_clusters([7])
    assert snap.cluster_id == 7
    assert snap.entries == []
    assert not api.clb_get_target_private_ips.called


def _snap_with(**entry_fields):
    from backend.db_periodic_task.clb_snapshot import CLBEntrySnapshot, ClusterCLBSnapshot

    entry = CLBEntrySnapshot(cluster_entry_id=11, entry="e", **entry_fields)
    return ClusterCLBSnapshot(cluster_id=1, checked_at=1.0, entries=[entry])


def test_execute_warns_when_entries_have_errors():
    snaps = [
        _snap_with(listener_rs=None, listener_rs_error="CLB listener RS query failed: down"),
        _snap_with(listener_rs=[], health_error="CLB target health query failed: down"),
        _snap_with(listener_rs=[], unhealthy_rs=[]),
    ]
    with patch.object(task_module, "snapshot_clusters", return_value=snaps), patch.object(
        task_module, "write_many"
    ), patch.object(task_module, "logger") as log:
        ClbSnapshotTask(config=ClbSnapshotTaskConfig()).execute({"cluster_ids": [1, 2, 3]})

    log.warning.assert_called_once()
    args = log.warning.call_args.args
    assert args[1:6] == (2, 3, 0, 1, 1)
    assert "down" in args[7]


def test_execute_logs_info_when_clean():
    with patch.object(
        task_module, "snapshot_clusters", return_value=[_snap_with(listener_rs=[], unhealthy_rs=[])]
    ), patch.object(task_module, "write_many"), patch.object(task_module, "logger") as log:
        ClbSnapshotTask(config=ClbSnapshotTaskConfig()).execute({"cluster_ids": [1]})
    log.warning.assert_not_called()
    log.info.assert_called_once()


def test_execute_writes_snapshots_once():
    snaps = [MagicMock(), MagicMock()]
    with patch.object(task_module, "snapshot_clusters", return_value=snaps) as snap_fn, patch.object(
        task_module, "write_many"
    ) as write:
        outcome = ClbSnapshotTask(config=ClbSnapshotTaskConfig()).execute({"cluster_ids": [1, 2]})
    snap_fn.assert_called_once_with([1, 2])
    write.assert_called_once_with(snaps)
    assert outcome.outcome == DispatchOutcomeType.SUCCESS


# ---------------------------------------------------------------- submit


def _patch_clb_clusters(cluster_ids):
    qs = MagicMock()
    qs.values_list.return_value = list(cluster_ids)
    return patch.object(task_module.ClusterEntry.objects, "filter", return_value=qs)


def _patch_task(enabled=True, outcome=DispatchOutcomeType.ENQUEUED):
    instance = MagicMock()
    instance.config = ClbSnapshotTaskConfig(enabled=enabled)
    instance.submit.side_effect = lambda items: [DispatchOutcome(outcome=outcome) for _ in items]
    return patch.object(task_module, "ClbSnapshotTask", return_value=instance), instance


def test_submit_skips_clusters_without_clb_and_batches_by_50():
    task_patch, instance = _patch_task()
    with task_patch, _patch_clb_clusters(range(1, 121)):
        summary = submit(list(range(1, 131)))

    [batches] = instance.submit.call_args.args
    assert [len(b["cluster_ids"]) for b in batches] == [50, 50, 20]
    assert summary.accepted == 120
    assert summary.skipped == 10
    assert summary.duplicate == summary.rejected == 0


def test_submit_counts_duplicates_and_rejections_by_cluster():
    task_patch, _ = _patch_task(outcome=DispatchOutcomeType.ENQUEUE_DUPLICATE)
    with task_patch, _patch_clb_clusters([1, 2, 3]):
        assert submit([1, 2, 3]).duplicate == 3

    task_patch, _ = _patch_task(outcome=DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED)
    with task_patch, _patch_clb_clusters([1, 2, 3]):
        assert submit([1, 2, 3]).rejected == 3


def test_submit_disabled_enqueues_nothing():
    task_patch, instance = _patch_task(enabled=False)
    with task_patch, _patch_clb_clusters([1, 2]) as entries:
        summary = submit([1, 2])
    assert not instance.submit.called
    assert not entries.called
    assert (summary.accepted, summary.duplicate, summary.rejected, summary.skipped) == (0, 0, 0, 0)


def test_submit_empty_input():
    task_patch, instance = _patch_task()
    with task_patch:
        summary = submit([])
    assert not instance.submit.called
    assert summary.accepted == 0


@pytest.mark.django_db
def test_resubmitting_same_list_is_duplicate():
    from backend.db_periodic_task.dispatch import routing

    def _clean():
        client = routing.conn_for_namespace(NameserviceQueue.namespace)
        keys = list(client.scan_iter(match=f"dispatch:{NameserviceQueue.namespace}:*", count=500))
        if keys:
            client.delete(*keys)

    _clean()
    try:
        with _patch_clb_clusters([1, 2, 3]):
            first = submit([1, 2, 3])
            second = submit([3, 2, 1])
        assert first.accepted == 3
        assert second.duplicate == 3
        assert second.accepted == 0
    finally:
        _clean()
