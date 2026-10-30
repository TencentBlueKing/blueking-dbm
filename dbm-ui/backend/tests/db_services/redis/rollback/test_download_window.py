# -*- coding: utf-8 -*-
import threading

import pytest
from django.db import connection

from backend.db_services.redis.rollback import download_window
from backend.db_services.redis.rollback.models import TbTendisRollbackPlan


def _plan_row(**kwargs):
    return TbTendisRollbackPlan.objects.create(bk_biz_id=1, cluster_id=2, **kwargs)


@pytest.mark.django_db
def test_reserve_open_release_and_is_idempotent():
    plan = _plan_row()
    assert download_window.read_batches(plan.id, "2.2.2.2") == {}

    assert download_window.reserve(plan.id, "2.2.2.2", 0, 300, 500) == 300
    # 300 more would exceed the 500 window of this plan.
    assert download_window.reserve(plan.id, "2.2.2.2", 1, 300, 500) == download_window.RESERVE_NO_WINDOW
    assert download_window.mark_open(plan.id, "2.2.2.2", 0, 11)

    entry = download_window.read_batches(plan.id, "2.2.2.2")[0]
    assert entry["state"] == download_window.DOWNLOAD_STATE_OPEN
    assert entry["bill_id"] == 11

    assert download_window.release(plan.id, "2.2.2.2", 0, download_window.DOWNLOAD_STATE_CLOSED) == 0
    # Releasing twice must not decrement again.
    assert download_window.release(plan.id, "2.2.2.2", 0, download_window.DOWNLOAD_STATE_CLOSED) == 0
    assert download_window.read_inflight(plan.id) == 0

    # A closed batch cannot be reserved again.
    assert download_window.reserve(plan.id, "2.2.2.2", 0, 10, 500) == download_window.RESERVE_OCCUPIED
    assert download_window.reserve(plan.id, "2.2.2.2", 1, 200, 500) == 200


@pytest.mark.django_db
def test_hosts_in_the_same_plan_share_the_window():
    plan = _plan_row()
    assert download_window.reserve(plan.id, "2.2.2.2", 0, 300, 500) == 300
    assert download_window.reserve(plan.id, "3.3.3.3", 0, 300, 500) == download_window.RESERVE_NO_WINDOW
    assert download_window.read_inflight(plan.id) == 300


@pytest.mark.django_db
def test_each_plan_has_its_own_window():
    first, second = _plan_row(), _plan_row()
    assert download_window.reserve(first.id, "2.2.2.2", 0, 500, 500) == 500
    assert download_window.reserve(second.id, "2.2.2.2", 0, 500, 500) == 500
    assert download_window.read_inflight(first.id) == 500
    assert download_window.read_inflight(second.id) == 500


@pytest.mark.django_db
def test_only_download_state_is_written():
    plan = _plan_row(plan={"keep": ["this"]})
    download_window.reserve(plan.id, "2.2.2.2", 0, 50, 500)
    download_window.mark_open(plan.id, "2.2.2.2", 0, 7)
    download_window.release(plan.id, "2.2.2.2", 0, download_window.DOWNLOAD_STATE_CLOSED)

    plan.refresh_from_db()
    assert plan.plan == {"keep": ["this"]}
    assert plan.download_state["inflight"] == 0
    assert plan.download_state["batches"]["2.2.2.2"]["0"]["state"] == download_window.DOWNLOAD_STATE_CLOSED


@pytest.mark.django_db(transaction=True)
def test_concurrent_reservations_do_not_exceed_the_plan_limit():
    if not connection.features.has_select_for_update:
        pytest.skip("database does not support select_for_update")
    plan = _plan_row()
    barrier = threading.Barrier(2)
    results, errors = [], []

    def worker(dest_ip):
        try:
            barrier.wait(timeout=5)
            results.append(download_window.reserve(plan.id, dest_ip, 0, 300, 500))
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(ip,)) for ip in ("2.2.2.2", "3.3.3.3")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert sorted(results) == sorted([300, download_window.RESERVE_NO_WINDOW])
    assert download_window.read_inflight(plan.id) == 300


@pytest.mark.parametrize(
    "total, interval",
    [(0, 10), (499, 10), (500, 20), (999, 20), (1000, 30), (1999, 30), (2000, 60), (5000, 60)],
)
def test_progress_interval_tiers(total, interval):
    assert download_window.progress_interval(total) == interval


def test_progress_line_contains_required_fields():
    line = download_window.format_progress(
        2000, 1240, [{"bill_id": 101, "doing": 30}, {"bill_id": 102, "doing": 10}], 3600
    )
    assert line.startswith("[")
    assert "62%" in line
    assert "done=1240" in line
    assert "wait=760" in line
    assert "bill=101" in line
    assert "open=2" in line
    assert "ETA=" in line
    assert len(line) <= download_window.MAX_PROGRESS_LINE


@pytest.mark.parametrize("elapsed", [0, 5, 10, 3600, 86400])
def test_progress_line_never_exceeds_eighty_characters(elapsed):
    line = download_window.format_progress(2000, 1, [{"bill_id": 1234567890123456789, "doing": 1}], elapsed)
    assert len(line) <= download_window.MAX_PROGRESS_LINE


def test_progress_eta_formats():
    assert download_window.format_progress(100, 50, [], 20).endswith("ETA=20s")
    assert download_window.format_progress(100, 50, [], 120).endswith("ETA=2m")
    assert download_window.format_progress(100, 50, [], 3900).endswith("ETA=1h5m")
    assert download_window.format_progress(100, 0, [], 3600).endswith("ETA=?")


def test_current_bill_prefers_the_busiest_then_the_smallest_id():
    line = download_window.format_progress(200, 100, [{"bill_id": 12, "doing": 5}, {"bill_id": 11, "doing": 5}], 60)
    assert "bill=11" in line


def test_progress_without_bills():
    line = download_window.format_progress(0, 0, [], 0)
    assert "100%" in line
    assert len(line) <= download_window.MAX_PROGRESS_LINE
