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
from typing import Any, Dict, Iterable, List, Optional

from django.db import transaction
from django.utils import timezone

from backend.db_services.redis.rollback.models import TbTendisRollbackPlan

# Plan-wide download window and its batch ledger live on the plan row, so a retry after a
# process restart or a Redis/cache wipe still sees which batches were already submitted:
#
#   TbTendisRollbackPlan.download_state
#     inflight                     task ids reserved but not finished
#     batches.<dest_ip>.<index>    {"bill_id": ..., "task_count": n, "state": ...}
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


def reserve(plan_id: int, dest_ip: str, batch_index: int, task_count: int, limit: int) -> int:
    """Reserve capacity and write the submitting row in one transaction.

    Returns the new inflight count, RESERVE_OCCUPIED when the batch already exists and is not
    failed, or RESERVE_NO_WINDOW when the plan's window has no room.
    """
    with transaction.atomic():
        state = _load_state(plan_id, for_update=True)
        entry = _batch(state, dest_ip, batch_index)
        if entry and entry.get("state") != DOWNLOAD_STATE_FAILED:
            return RESERVE_OCCUPIED
        count = int(task_count)
        inflight = int(state["inflight"])
        if inflight + count > int(limit):
            return RESERVE_NO_WINDOW
        _host_batches(state, dest_ip)[str(int(batch_index))] = {
            "bill_id": None,
            "task_count": count,
            "state": DOWNLOAD_STATE_SUBMITTING,
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


def _current_bill(open_bills: Iterable[Dict[str, Any]]) -> Optional[int]:
    """The bill doing the most work; ties go to the smallest id."""
    candidates = [bill for bill in open_bills if bill.get("bill_id") is not None]
    if not candidates:
        return None
    return sorted(candidates, key=lambda bill: (-int(bill.get("doing") or 0), int(bill["bill_id"])))[0]["bill_id"]


def format_progress(total: int, done: int, open_bills: List[Dict[str, Any]], elapsed: float) -> str:
    """One progress line, at most MAX_PROGRESS_LINE characters.

    ``open_bills`` items are ``{"bill_id": int, "doing": int}`` for the host's open bills.
    """
    total = max(int(total), 0)
    done = min(max(int(done), 0), total) if total else 0
    percent = 100 if total == 0 else done * 100 // total
    waiting = max(total - done, 0)
    current = _current_bill(open_bills)
    open_count = len(open_bills)
    eta = _format_eta((total - done) * elapsed / done) if elapsed >= PROGRESS_MIN_SAMPLE_SECONDS and done else "?"

    def render(width: int, with_open: bool) -> str:
        parts = [
            _bar(done, total, width),
            "{}%".format(percent),
            "done={}".format(done),
            "wait={}".format(waiting),
        ]
        if current is not None:
            parts.append("bill={}".format(current))
        if with_open and open_count > 1:
            parts.append("open={}".format(open_count))
        parts.append("ETA={}".format(eta))
        return " ".join(parts)

    # Prefer the full line; then drop the open count, then shrink the bar. The bill id is
    # never shortened.
    for width in (PROGRESS_BAR_WIDTH, 12, 8, 6):
        for with_open in (True, False) if width == PROGRESS_BAR_WIDTH else (False,):
            line = render(width, with_open)
            if len(line) <= MAX_PROGRESS_LINE:
                return line
    return render(6, False)
