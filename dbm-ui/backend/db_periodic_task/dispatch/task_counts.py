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

import logging
import time
from collections import defaultdict
from typing import Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.config import (
    TASK_COUNTS_REBUILD_FORCE_SECONDS,
    TASK_COUNTS_REBUILD_REQUEST_TTL_SECONDS,
    TASK_COUNTS_REBUILD_RETRY_SECONDS,
    TASK_COUNTS_REBUILD_SCAN_COUNT,
    TASK_COUNTS_REBUILD_SCAN_PAUSE_SECONDS,
)
from backend.db_periodic_task.dispatch.job import resolve_task_key_from_job_id
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.metrics import decode_text
from backend.db_periodic_task.dispatch.queue import (
    KEY_REGISTERED,
    TASK_COUNTS_TTL_SECONDS,
    DispatchQueue,
    try_acquire_ttl_gate,
)

logger = logging.getLogger("root")

# Pseudo-task key collecting members whose job_id prefix matches no registered
# task (e.g. jobs left behind by an unregistered task). Bucketing them keeps
# the rebuild completing instead of aborting the whole namespace, and the field
# doubles as an alerting signal for stale membership.
UNRESOLVED_TASK_KEY = "__unresolved__"

# Replace the derived per-task hash only if queue totals still match the scan.
# Admission/reservation/finalize scripts cannot interleave with this Lua check.
REPLACE_TASK_COUNTS_LUA = """
local pending = tonumber(redis.call('ZCARD', KEYS[1]))
local reserved = tonumber(redis.call('ZCARD', KEYS[2]))
local expected_pending = tonumber(ARGV[1])
local expected_reserved = tonumber(ARGV[2])
if pending ~= expected_pending or reserved ~= expected_reserved then
    return 0
end

local field_count = tonumber(ARGV[3])
redis.call('DEL', KEYS[3])
for index = 1, field_count do
    local offset = 5 + ((index - 1) * 2)
    redis.call('HSET', KEYS[3], ARGV[offset], ARGV[offset + 1])
end
if field_count > 0 then
    redis.call('EXPIRE', KEYS[3], ARGV[4])
end
return 1
"""
_replace_task_counts_script = compile_script(REPLACE_TASK_COUNTS_LUA)


def _parse_task_count_field(field: str) -> Optional[tuple[str, str]]:
    """Return ``(kind, task_key)`` for a ``task_counts`` hash field, else ``None``."""
    if field.startswith("pending:"):
        return "pending", field[len("pending:") :]
    if field.startswith("reserved:"):
        return "reserved", field[len("reserved:") :]
    return None


def _summarize_task_counts_hash(raw: dict) -> Optional[tuple[int, int]]:
    """Parse ``task_counts`` hash into pending/reserved sums.

    Returns ``None`` when a field value is invalid (treated as drift evidence).
    """
    pending_sum = 0
    reserved_sum = 0

    for raw_field, raw_value in raw.items():
        parsed = _parse_task_count_field(decode_text(raw_field))
        if parsed is None:
            continue
        kind, _task_key = parsed
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        if kind == "pending":
            pending_sum += value
        else:
            reserved_sum += value
    return pending_sum, reserved_sum


def _task_count_mapping(
    pending_counts: dict[str, int],
    reserved_counts: dict[str, int],
) -> dict[str, int]:
    mapping = {
        DispatchQueue.pending_count_field(task_key): count for task_key, count in pending_counts.items() if count > 0
    }
    mapping.update(
        {
            DispatchQueue.reserved_count_field(task_key): count
            for task_key, count in reserved_counts.items()
            if count > 0
        }
    )
    return mapping


class TaskCounts:
    """Maintenance for the rebuildable per-task membership hash of one namespace.

    All operations bind to a queue class (``queue_cls``) the same way the
    admission/reservation/lifecycle helpers do. The hash mirrors
    pending/reserved ZSET membership per task and is repaired out of band by
    ``dispatch_task_counts_maintenance`` when it drifts or expires.
    """

    @classmethod
    def _rebuilt_key(cls, queue_cls: type[DispatchQueue]) -> str:
        return f"dispatch:{queue_cls.namespace}:task_counts_rebuilt"

    @classmethod
    def _rebuild_requested_key(cls, queue_cls: type[DispatchQueue]) -> str:
        return f"dispatch:{queue_cls.namespace}:task_counts_rebuild_requested"

    @classmethod
    def _rebuild_attempt_key(cls, queue_cls: type[DispatchQueue]) -> str:
        return f"dispatch:{queue_cls.namespace}:task_counts_rebuild_attempt"

    @classmethod
    def hard_rebuild_due(cls, queue_cls: type[DispatchQueue]) -> bool:
        """True when the daily hard-audit safety window has expired."""
        try:
            return not bool(queue_cls.conn().exists(cls._rebuilt_key(queue_cls)))
        except Exception as exc:
            logger.warning(
                "dispatch: task_counts hard-rebuild check failed namespace=%s: %s",
                queue_cls.namespace,
                exc,
            )
            return False

    @classmethod
    def rebuild_requested(cls, queue_cls: type[DispatchQueue]) -> bool:
        try:
            return bool(queue_cls.conn().exists(cls._rebuild_requested_key(queue_cls)))
        except Exception as exc:
            logger.warning(
                "dispatch: task_counts rebuild-request check failed namespace=%s: %s",
                queue_cls.namespace,
                exc,
            )
            return False

    @classmethod
    def request_rebuild(cls, queue_cls: type[DispatchQueue], reason: str) -> bool:
        """Request out-of-band repair without scanning from the pump."""
        try:
            queue_cls.conn().set(
                cls._rebuild_requested_key(queue_cls),
                str(reason or "unspecified"),
                ex=TASK_COUNTS_REBUILD_REQUEST_TTL_SECONDS,
            )
            return True
        except Exception as exc:
            logger.warning(
                "dispatch: task_counts rebuild request failed namespace=%s reason=%s: %s",
                queue_cls.namespace,
                reason,
                exc,
            )
            return False

    @classmethod
    def try_start_rebuild(cls, queue_cls: type[DispatchQueue]) -> bool:
        """Apply one-hour retry backoff before an independent full scan."""
        return try_acquire_ttl_gate(
            cls._rebuild_attempt_key(queue_cls),
            TASK_COUNTS_REBUILD_RETRY_SECONDS,
            client=queue_cls.conn(),
        )

    @classmethod
    def mark_rebuilt(cls, queue_cls: type[DispatchQueue]) -> bool:
        """Commit successful daily audit state and clear request/backoff."""
        try:
            pipe = queue_cls.conn().pipeline(transaction=False)
            pipe.set(cls._rebuilt_key(queue_cls), "1", ex=TASK_COUNTS_REBUILD_FORCE_SECONDS)
            pipe.delete(
                cls._rebuild_requested_key(queue_cls),
                cls._rebuild_attempt_key(queue_cls),
            )
            pipe.execute()
            return True
        except Exception as exc:
            logger.warning(
                "dispatch: task_counts rebuild marker update failed namespace=%s: %s",
                queue_cls.namespace,
                exc,
            )
            return False

    @classmethod
    def counts_drifted(cls, queue_cls: type[DispatchQueue]) -> bool:
        """Cheap drift check: ``ZCARD`` vs hash field sums (no per-task ZSCAN)."""
        try:
            pending_z = queue_cls.pending_count()
            reserved_z = queue_cls.reserved_count()
            if pending_z < 0 or reserved_z < 0:
                return False
            raw = queue_cls.conn().hgetall(queue_cls.task_counts_key()) or {}
        except Exception as exc:
            logger.warning(
                "dispatch: task_counts drift check failed namespace=%s: %s",
                queue_cls.namespace,
                exc,
            )
            return False

        summarized = _summarize_task_counts_hash(raw)
        if summarized is None:
            return True
        pending_sum, reserved_sum = summarized
        return abs(pending_sum - pending_z) > 0 or abs(reserved_sum - reserved_z) > 0

    @classmethod
    def _scan_zset(
        cls,
        queue_cls: type[DispatchQueue],
        zset_key: str,
        registered: list[str],
        *,
        deadline_at: Optional[float],
        scan_count: int,
        scan_pause_seconds: float,
    ) -> Optional[tuple[dict[str, int], int, int, int]]:
        """Return counts, pages, scanned members, and unresolved members."""
        counts: dict[str, int] = defaultdict(int)
        pages = 0
        scanned = 0
        unresolved = 0
        cursor = 0
        while True:
            if deadline_at is not None and time.monotonic() >= deadline_at:
                return None
            cursor, members = queue_cls.conn().zscan(zset_key, cursor, count=max(1, int(scan_count)))
            pages += 1
            scanned += len(members or [])
            for raw_id, _score in members or []:
                task_key = resolve_task_key_from_job_id(decode_text(raw_id), registered)
                if task_key:
                    counts[task_key] += 1
                else:
                    unresolved += 1
                    counts[UNRESOLVED_TASK_KEY] += 1
            if cursor == 0:
                return dict(counts), pages, scanned, unresolved
            pause = max(0.0, float(scan_pause_seconds))
            if pause:
                time.sleep(pause)

    @classmethod
    def _replace_if_current(
        cls,
        queue_cls: type[DispatchQueue],
        mapping: dict[str, int],
        *,
        expected_pending: int,
        expected_reserved: int,
    ) -> bool:
        args: list[object] = [
            expected_pending,
            expected_reserved,
            len(mapping),
            TASK_COUNTS_TTL_SECONDS,
        ]
        for field, value in mapping.items():
            args.extend([field, value])
        return bool(
            eval_script(
                _replace_task_counts_script,
                client=queue_cls.conn(),
                keys=[
                    queue_cls.pending_key(),
                    queue_cls.reserved_key(),
                    queue_cls.task_counts_key(),
                ],
                args=args,
            )
        )

    @classmethod
    def rebuild(
        cls,
        queue_cls: type[DispatchQueue],
        *,
        deadline_at: Optional[float] = None,
        scan_count: int = TASK_COUNTS_REBUILD_SCAN_COUNT,
        scan_pause_seconds: float = TASK_COUNTS_REBUILD_SCAN_PAUSE_SECONDS,
    ) -> Optional[dict[str, int]]:
        """Rebuild ``task_counts`` Hash from pending/reserved ZSET membership.

        Runs only in independent maintenance. The final Lua replacement checks
        current ZCARD totals against scanned totals, so common concurrent queue
        changes abort without overwriting the live derived hash.
        """
        started_at = time.monotonic()
        try:
            registered = [decode_text(key) for key in (routing.global_conn().hkeys(KEY_REGISTERED) or [])]
        except Exception:
            registered = []

        try:
            pending_scan = cls._scan_zset(
                queue_cls,
                queue_cls.pending_key(),
                registered,
                deadline_at=deadline_at,
                scan_count=scan_count,
                scan_pause_seconds=scan_pause_seconds,
            )
            reserved_scan = cls._scan_zset(
                queue_cls,
                queue_cls.reserved_key(),
                registered,
                deadline_at=deadline_at,
                scan_count=scan_count,
                scan_pause_seconds=scan_pause_seconds,
            )
            if pending_scan is None or reserved_scan is None:
                logger.warning(
                    "dispatch: rebuild_task_counts aborted by deadline namespace=%s",
                    queue_cls.namespace,
                )
                return None
            pending_counts, pending_pages, pending_scanned, pending_unresolved = pending_scan
            reserved_counts, reserved_pages, reserved_scanned, reserved_unresolved = reserved_scan
            pages = pending_pages + reserved_pages
            scanned = pending_scanned + reserved_scanned
            unresolved = pending_unresolved + reserved_unresolved
            if unresolved:
                # Bucketed under ``pending:__unresolved__`` / ``reserved:__unresolved__``
                # so the totals still reconcile with ZCARD; the log line is the
                # alert signal for stale membership (e.g. a task was unregistered
                # while its jobs were still queued).
                logger.warning(
                    "dispatch: rebuild task_counts unresolved namespace=%s members=%d scanned=%d pages=%d",
                    queue_cls.namespace,
                    unresolved,
                    scanned,
                    pages,
                )
            if deadline_at is not None and time.monotonic() >= deadline_at:
                logger.warning(
                    "dispatch: rebuild_task_counts aborted by deadline namespace=%s",
                    queue_cls.namespace,
                )
                return None
            mapping = _task_count_mapping(pending_counts, reserved_counts)
            expected_pending = sum(pending_counts.values())
            expected_reserved = sum(reserved_counts.values())
            replaced = cls._replace_if_current(
                queue_cls,
                mapping,
                expected_pending=expected_pending,
                expected_reserved=expected_reserved,
            )
            if not replaced:
                logger.warning(
                    "dispatch: rebuild task_counts queue changed namespace=%s scanned=%d pages=%d",
                    queue_cls.namespace,
                    scanned,
                    pages,
                )
                return None
            logger.info(
                "dispatch: rebuilt task_counts namespace=%s scanned=%d pages=%d duration=%.3fs fields=%d",
                queue_cls.namespace,
                scanned,
                pages,
                time.monotonic() - started_at,
                len(mapping),
            )
            return dict(mapping)
        except Exception as exc:
            logger.warning("dispatch: rebuild_task_counts failed namespace=%s: %s", queue_cls.namespace, exc)
            return None
