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
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db import transaction
from django.utils import timezone

from backend.db_services.redis.rollback.constants import (
    DOWNLOAD_BATCH_SIZE,
    DOWNLOAD_INFLIGHT_TASK_LIMIT,
    DOWNLOAD_MIN_BATCH_SIZE,
)
from backend.db_services.redis.rollback.models import TbTendisRollbackPlan

# Plan-wide download window and its batch ledger live on the plan row, so a retry after a
# process restart or a Redis/cache wipe still sees which batches were already submitted:
#
#   TbTendisRollbackPlan.download_state
#     inflight                     task ids reserved but not finished
#     batches.<dest_ip>.<index>    {"bill_id": ..., "task_count": n, "state": ...}
#                                  + "lost_bills"/"lost_resubmits" once a bill was lost
#
# Every mutation locks that one row in a transaction: the counter and the ledger change
# atomically, and concurrent hosts of the same plan serialize on the row lock.
DOWNLOAD_STATE_SUBMITTING = "submitting"
DOWNLOAD_STATE_OPEN = "open"
DOWNLOAD_STATE_CLOSED = "closed"
DOWNLOAD_STATE_FAILED = "failed"

# reserve() results besides the new inflight count (>= 0).
RESERVE_OCCUPIED = -1
RESERVE_NO_WINDOW = -2

LOST_HISTORY_KEYS = ("lost_bills", "lost_resubmits")

MAX_PROGRESS_LINE = 80
PROGRESS_BAR_WIDTH = 16
# A progress line is printed once per interval; the interval grows with the host's file count
# so large rollbacks do not flood the log page.
PROGRESS_INTERVAL_TIERS = ((500, 10), (1000, 20), (2000, 30))
PROGRESS_INTERVAL_DEFAULT = 60
# ETA is only meaningful after a few seconds of samples.
PROGRESS_MIN_SAMPLE_SECONDS = 10


def _load_state(plan_id: int, for_update: bool = False) -> Dict[str, Any]:
    """The plan's download state; lock the row when the caller will change it."""
    query = TbTendisRollbackPlan.objects.only("id", "download_state")
    if for_update:
        query = query.select_for_update()
    row = query.get(id=int(plan_id))
    state = dict(row.download_state or {})
    state["inflight"] = int(state.get("inflight") or 0)
    if not isinstance(state.get("batches"), dict):
        state["batches"] = {}
    return state


def _save_state(plan_id: int, state: Dict[str, Any]) -> None:
    # RollbackPlan.save() only updates plan / ticket_id, so this cannot clobber the plan JSON.
    TbTendisRollbackPlan.objects.filter(id=int(plan_id)).update(download_state=state, update_at=timezone.now())


def _host_batches(state: Dict[str, Any], dest_ip: str) -> Dict[str, Any]:
    host = state["batches"].get(dest_ip)
    if not isinstance(host, dict):
        host = {}
        state["batches"][dest_ip] = host
    return host


def _batch(state: Dict[str, Any], dest_ip: str, batch_index: int) -> Optional[Dict[str, Any]]:
    host = state["batches"].get(dest_ip)
    if not isinstance(host, dict):
        return None
    entry = host.get(str(int(batch_index)))
    return entry if isinstance(entry, dict) else None


def batch_size_for_hosts(host_count: int, limit: int = DOWNLOAD_INFLIGHT_TASK_LIMIT) -> int:
    """Task ids per bill, scaled to the plan's active target hosts inside ``[min, max]``."""
    hosts = max(int(host_count or 0), 1)
    return min(DOWNLOAD_BATCH_SIZE, max(DOWNLOAD_MIN_BATCH_SIZE, int(limit) // hosts))


def _host_counts(host_ledger: Any) -> Tuple[int, int]:
    """``(closed_tasks, inflight_tasks)`` recorded for one host."""
    if not isinstance(host_ledger, dict):
        return 0, 0
    closed = 0
    inflight = 0
    for entry in host_ledger.values():
        if not isinstance(entry, dict):
            continue
        count = max(int(entry.get("task_count") or 0), 0)
        entry_state = entry.get("state")
        if entry_state == DOWNLOAD_STATE_CLOSED:
            closed += count
        elif entry_state in (DOWNLOAD_STATE_OPEN, DOWNLOAD_STATE_SUBMITTING):
            inflight += count
    return closed, inflight


def peer_headroom(
    batches_by_host: Dict[str, Any],
    dest_ip: str,
    host_totals: Optional[Dict[str, int]],
    batch_size: Optional[int],
    limit: int,
    failed_hosts: Optional[Set[str]] = None,
) -> int:
    """Window capacity kept free for unfinished peers so one host cannot starve the others.

    Finished or failed hosts drop out of ``active`` immediately (work-conserving). When the
    window holds at least one batch per active host, each peer retains its floor share up to
    its remaining unsubmitted tasks; when active hosts outnumber slots (>20 hosts), a host
    that has already progressed yields to idle peers strictly behind it.
    """
    if not host_totals:
        return 0
    failed = failed_hosts or set()
    counts: Dict[str, Tuple[int, int]] = {}
    active: List[str] = []
    for ip, raw_total in host_totals.items():
        total = int(raw_total or 0)
        if total <= 0:
            continue
        closed, inflight = _host_counts((batches_by_host or {}).get(ip))
        counts[ip] = (closed, inflight)
        if closed >= total:
            continue
        if ip != dest_ip and ip in failed:
            continue
        active.append(ip)
    if len(active) <= 1 or dest_ip not in active:
        return 0
    step = max(int(batch_size or batch_size_for_hosts(len(active), limit)), 1)
    total_slots = max(int(limit) // step, 1)
    floor_slots = total_slots // len(active)
    reserved = 0
    if floor_slots >= 1:
        entitled = floor_slots * step
        for other in active:
            if other == dest_ip:
                continue
            closed, inflight = counts[other]
            unsubmitted = max(int(host_totals[other]) - closed - inflight, 0)
            if inflight < entitled and unsubmitted > 0:
                reserved += min(unsubmitted, entitled - inflight)
        return reserved
    my_closed, my_inflight = counts[dest_ip]
    my_progress = my_closed + my_inflight
    for other in active:
        if other == dest_ip:
            continue
        closed, inflight = counts[other]
        if inflight == 0 and (closed + inflight) < my_progress:
            unsubmitted = max(int(host_totals[other]) - closed, 0)
            reserved += min(unsubmitted, step)
    return reserved


def reserve(
    plan_id: int,
    dest_ip: str,
    batch_index: int,
    task_count: int,
    limit: int,
    host_totals: Optional[Dict[str, int]] = None,
    batch_size: Optional[int] = None,
) -> int:
    """Reserve capacity and write the submitting row in one transaction.

    Returns the new inflight count, RESERVE_OCCUPIED when the batch already exists and is not
    failed, or RESERVE_NO_WINDOW when the plan's window (or peer fair share) has no room.
    """
    with transaction.atomic():
        state = _load_state(plan_id, for_update=True)
        entry = _batch(state, dest_ip, batch_index)
        if entry and entry.get("state") != DOWNLOAD_STATE_FAILED:
            return RESERVE_OCCUPIED
        failed = set(state.get("failed_hosts") or [])
        was_failed = dest_ip in failed
        if was_failed:
            failed.discard(dest_ip)
            if failed:
                state["failed_hosts"] = sorted(failed)
            else:
                state.pop("failed_hosts", None)
        count = int(task_count)
        limit_val = int(limit)
        inflight = int(state["inflight"])
        reserved = peer_headroom(state["batches"], dest_ip, host_totals, batch_size, limit_val, failed)
        if inflight + count > limit_val or (inflight > 0 and inflight + count + reserved > limit_val):
            if was_failed:
                _save_state(plan_id, state)
            return RESERVE_NO_WINDOW
        # Lost-bill history survives the resubmission, so the resubmit limit holds across retries.
        history = {key: entry[key] for key in LOST_HISTORY_KEYS if entry and key in entry}
        _host_batches(state, dest_ip)[str(int(batch_index))] = {
            "bill_id": None,
            "task_count": count,
            "state": DOWNLOAD_STATE_SUBMITTING,
            **history,
        }
        state["inflight"] = inflight + count
        _save_state(plan_id, state)
        return inflight + count


def mark_open(plan_id: int, dest_ip: str, batch_index: int, bill_id: int) -> bool:
    with transaction.atomic():
        state = _load_state(plan_id, for_update=True)
        entry = _batch(state, dest_ip, batch_index)
        if not entry or entry.get("state") != DOWNLOAD_STATE_SUBMITTING:
            return False
        entry["state"] = DOWNLOAD_STATE_OPEN
        entry["bill_id"] = int(bill_id)
        _save_state(plan_id, state)
        return True


def release(plan_id: int, dest_ip: str, batch_index: int, new_state: str) -> int:
    """Move a submitting/open row to closed/failed and release its task count.

    The state transition is checked under the row lock, so releasing twice decrements once.
    """
    with transaction.atomic():
        state = _load_state(plan_id, for_update=True)
        entry = _batch(state, dest_ip, batch_index)
        if not entry or entry.get("state") not in (DOWNLOAD_STATE_OPEN, DOWNLOAD_STATE_SUBMITTING):
            return int(state["inflight"])
        entry["state"] = new_state
        if new_state == DOWNLOAD_STATE_FAILED:
            failed = set(state.get("failed_hosts") or [])
            failed.add(dest_ip)
            state["failed_hosts"] = sorted(failed)
        left = max(int(state["inflight"]) - int(entry.get("task_count") or 0), 0)
        state["inflight"] = left
        _save_state(plan_id, state)
        return left


def release_lost(plan_id: int, dest_ip: str, batch_index: int) -> int:
    """Fail an open batch whose bill the backup system lost, so reserve() can take it again.

    The lost bill is appended to ``lost_bills`` and ``lost_resubmits`` counts it, in the same
    transaction that releases the task count.
    """
    with transaction.atomic():
        state = _load_state(plan_id, for_update=True)
        entry = _batch(state, dest_ip, batch_index)
        if not entry or entry.get("state") != DOWNLOAD_STATE_OPEN or entry.get("bill_id") is None:
            return int(state["inflight"])
        entry["state"] = DOWNLOAD_STATE_FAILED
        entry["lost_bills"] = list(entry.get("lost_bills") or []) + [int(entry["bill_id"])]
        entry["lost_resubmits"] = int(entry.get("lost_resubmits") or 0) + 1
        left = max(int(state["inflight"]) - int(entry.get("task_count") or 0), 0)
        state["inflight"] = left
        _save_state(plan_id, state)
        return left


def read_batches(plan_id: int, dest_ip: str) -> Dict[int, Dict[str, Any]]:
    """All ledger rows of one host, keyed by batch index."""
    entries: Dict[int, Dict[str, Any]] = {}
    host = _load_state(plan_id)["batches"].get(dest_ip)
    if not isinstance(host, dict):
        return entries
    for key, value in host.items():
        try:
            batch_index = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        entry = dict(value)
        entry["batch_index"] = batch_index
        entries[batch_index] = entry
    return entries


def read_inflight(plan_id: int) -> int:
    return int(_load_state(plan_id)["inflight"])


def progress_interval(total: int) -> int:
    for limit, interval in PROGRESS_INTERVAL_TIERS:
        if total < limit:
            return interval
    return PROGRESS_INTERVAL_DEFAULT


def _format_eta(seconds: Optional[float]) -> str:
    if seconds is None:
        return "?"
    seconds = max(int(seconds), 0)
    if seconds < 60:
        return "{}s".format(seconds)
    minutes = (seconds + 59) // 60
    if minutes < 60:
        return "{}m".format(minutes)
    hours, minutes = divmod(minutes, 60)
    return "{}h{}m".format(hours, minutes)


def _bar(done: int, total: int, width: int) -> str:
    if total <= 0:
        filled = width
    else:
        filled = min(width, max(int(done * width / total), 0))
    return "[{}{}]".format("█" * filled, "░" * (width - filled))


def format_progress(total: int, done: int, open_bills: List[Dict[str, Any]], elapsed: float) -> str:
    """One progress line, at most MAX_PROGRESS_LINE characters.

    ``open_bills`` items are ``{"bill_id": int, "doing": int}`` for the host's open bills.
    """
    total = max(int(total), 0)
    done = min(max(int(done), 0), total) if total else 0
    percent = 100 if total == 0 else done * 100 // total
    waiting = max(total - done, 0)
    open_count = len(open_bills)
    eta = _format_eta((total - done) * elapsed / done) if elapsed >= PROGRESS_MIN_SAMPLE_SECONDS and done else "?"

    def render(width: int, with_open: bool) -> str:
        parts = [
            _bar(done, total, width),
            "{}%".format(percent),
            "done={}".format(done),
            "waiting={}".format(waiting),
        ]
        if with_open and open_count > 1:
            parts.append("open={}".format(open_count))
        parts.append("ETA={}".format(eta))
        return " ".join(parts)

    # Prefer the full line; then drop the open count, then shrink the bar.
    for width in (PROGRESS_BAR_WIDTH, 12, 8, 6):
        for with_open in (True, False) if width == PROGRESS_BAR_WIDTH else (False,):
            line = render(width, with_open)
            if len(line) <= MAX_PROGRESS_LINE:
                return line
    return render(6, False)
