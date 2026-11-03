from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from backend.db_periodic_task.clb_snapshot.snapshot import (
    CLB_SNAPSHOT_TTL_SECONDS,
    CLBEntrySnapshot,
    ClusterCLBSnapshot,
    get_many,
    write_many,
)

LOCMEM_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "clb-snapshot"}}


@pytest.fixture(autouse=True)
def locmem_cache():
    with override_settings(CACHES=LOCMEM_CACHES):
        cache.clear()
        yield
        cache.clear()


def _snapshot(cluster_id: int, checked_at: float = 1000.0, **entry_fields) -> ClusterCLBSnapshot:
    entry = CLBEntrySnapshot(
        cluster_entry_id=cluster_id * 10,
        entry=f"cache{cluster_id}.example.db",
        clb_id="lb-1",
        listener_id="lbl-1",
        region="ap-test",
        **entry_fields,
    )
    return ClusterCLBSnapshot(cluster_id=cluster_id, checked_at=checked_at, entries=[entry])


def test_round_trip_keeps_unknown_distinct_from_empty():
    write_many(
        [
            _snapshot(1, listener_rs=["1.1.1.1:30000"], unhealthy_rs=[]),
            _snapshot(2, listener_rs=None, listener_rs_error="boom"),
        ]
    )
    result = get_many([1, 2])

    assert result[1].entries[0].listener_rs == ["1.1.1.1:30000"]
    assert result[1].entries[0].unhealthy_rs == []
    assert result[2].entries[0].listener_rs is None
    assert result[2].entries[0].unhealthy_rs is None
    assert result[2].entries[0].listener_rs_error == "boom"
    assert result[1].checked_at == 1000.0


def test_partial_hits_return_none_for_missing():
    write_many([_snapshot(1)])
    result = get_many([1, 2])
    assert result[1] is not None
    assert result[2] is None


@pytest.mark.parametrize(
    "corrupt",
    [
        {"checked_at": 1.0, "entries": []},
        {"cluster_id": 2, "checked_at": "not-a-time", "entries": []},
        {"cluster_id": 2, "checked_at": 1.0, "entries": [{"entry": "no-entry-id"}]},
        {"cluster_id": 2, "checked_at": 1.0, "entries": ["not-a-dict"]},
    ],
)
def test_corrupt_record_only_affects_its_cluster(corrupt):
    write_many([_snapshot(1), _snapshot(3)])
    cache.set("dbm:clb_snapshot:2", corrupt)
    result = get_many([1, 2, 3])
    assert result[1] is not None
    assert result[2] is None
    assert result[3] is not None


def test_new_snapshot_replaces_previous():
    write_many([_snapshot(1, checked_at=1000.0, listener_rs=["1.1.1.1:30000"])])
    write_many([_snapshot(1, checked_at=2000.0, listener_rs=["2.2.2.2:30000"])])
    snap = get_many([1])[1]
    assert snap.checked_at == 2000.0
    assert snap.entries[0].listener_rs == ["2.2.2.2:30000"]


def test_write_uses_ttl_above_48_hours():
    with patch("backend.db_periodic_task.clb_snapshot.snapshot.cache") as mocked:
        write_many([_snapshot(1)])
    assert mocked.set_many.call_args.kwargs["timeout"] == CLB_SNAPSHOT_TTL_SECONDS
    assert CLB_SNAPSHOT_TTL_SECONDS >= 72 * 3600


def test_get_many_does_not_touch_name_service():
    write_many([_snapshot(1)])
    with patch("backend.components.NameServiceApi") as api:
        get_many([1])
    assert not api.mock_calls


def test_entry_by_id():
    snap = _snapshot(1)
    assert snap.entry_by_id(10) is snap.entries[0]
    assert snap.entry_by_id(99) is None


def test_empty_inputs():
    write_many([])
    assert get_many([]) == {}
