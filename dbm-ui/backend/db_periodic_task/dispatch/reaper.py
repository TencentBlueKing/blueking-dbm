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
from typing import Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.job import resolve_task_key_from_job_id, work_item_id_from_job_id
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.metrics import decode_text
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.queue import (
    KEY_JOB_PREFIX,
    KEY_REGISTERED,
    TASK_COUNTS_TTL_SECONDS,
    DispatchQueue,
)

logger = logging.getLogger("root")

# How long a persisted reap cursor stays valid without refresh. The pump rewrites
# it every cleanup interval (~60s); if the pump is down longer than this the
# cursor lapses and the next scan restarts from the head (same as before).
REAP_CURSOR_TTL_SECONDS = 10 * 60

# Orphan reap: ZREM x 2 + conditional counter decrement in one atomic script,
# matching the finalize/requeue guarantees. Doing ZREM in a pipeline and the
# HINCRBYs later on the Python side would let a concurrent reserve/finalize
# (or a crash between the two steps) drift the rebuildable counters.
PURGE_JOB_LUA = """
local pending_removed = redis.call('ZREM', KEYS[1], ARGV[1])
local reserved_removed = redis.call('ZREM', KEYS[2], ARGV[1])
if ARGV[2] ~= '' and pending_removed > 0 then
    local value = tonumber(redis.call('HINCRBY', KEYS[3], ARGV[2], -1))
    if value <= 0 then
        redis.call('HDEL', KEYS[3], ARGV[2])
    end
end
if ARGV[3] ~= '' and reserved_removed > 0 then
    local value = tonumber(redis.call('HINCRBY', KEYS[3], ARGV[3], -1))
    if value <= 0 then
        redis.call('HDEL', KEYS[3], ARGV[3])
    end
end
if pending_removed > 0 or reserved_removed > 0 then
    redis.call('EXPIRE', KEYS[3], ARGV[4])
end
return {pending_removed, reserved_removed}
"""
_purge_job_script = compile_script(PURGE_JOB_LUA)


def _registered_task_keys() -> list[str]:
    try:
        return [decode_text(key) for key in (routing.global_conn().hkeys(KEY_REGISTERED) or [])]
    except Exception:
        return []


class OrphanReaper:
    """Purge jobs whose payload is gone or whose wait deadline has expired.

    All operations bind to a queue class (``queue_cls``) and keep the same
    atomicity guarantees as finalize/requeue so concurrent reserve/finalize
    cannot drift the derived per-task counters.
    """

    @classmethod
    def _reap_cursor_key(cls, zset_key: str) -> str:
        return f"{zset_key}:reap_cursor"

    @classmethod
    def _read_reap_cursor(cls, queue_cls: type[DispatchQueue], zset_key: str) -> int:
        """Return the persisted ZSCAN cursor for ``zset_key`` (0 = start from head)."""
        try:
            raw = queue_cls.conn().get(cls._reap_cursor_key(zset_key))
            return int(raw) if raw is not None else 0
        except Exception:
            return 0

    @classmethod
    def _write_reap_cursor(cls, queue_cls: type[DispatchQueue], zset_key: str, cursor: int) -> None:
        try:
            queue_cls.conn().set(
                cls._reap_cursor_key(zset_key),
                str(max(0, int(cursor))),
                ex=REAP_CURSOR_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("dispatch: reap cursor write failed key=%s: %s", zset_key, exc)

    @classmethod
    def _clear_reap_cursor(cls, queue_cls: type[DispatchQueue], zset_key: str) -> None:
        try:
            queue_cls.conn().delete(cls._reap_cursor_key(zset_key))
        except Exception as exc:
            logger.warning("dispatch: reap cursor clear failed key=%s: %s", zset_key, exc)

    @classmethod
    def purge_job(cls, queue_cls: type[DispatchQueue], job_id: str, *, task_key: str = "") -> tuple[int, int]:
        """Remove ``job_id`` from this queue's pending/reserved zsets; adjust counters.

        Runs as one Lua script so the reap path keeps the same atomicity as
        finalize/requeue: no interleaving between ZREM and the counter updates.

        Returns ``(pending_removed, reserved_removed)`` so callers can skip no-op work.
        """
        pending_removed, reserved_removed = eval_script(
            _purge_job_script,
            client=queue_cls.conn(),
            keys=[queue_cls.pending_key(), queue_cls.reserved_key(), queue_cls.task_counts_key()],
            args=[
                job_id,
                queue_cls.pending_count_field(task_key) if task_key else "",
                queue_cls.reserved_count_field(task_key) if task_key else "",
                TASK_COUNTS_TTL_SECONDS,
            ],
        )
        return int(pending_removed or 0), int(reserved_removed or 0)

    @classmethod
    def discard_orphaned_job(
        cls,
        queue_cls: type[DispatchQueue],
        job_id: str,
        *,
        task_key: str = "",
        namespace: str = "",
        work_item_id: str = "",
        outcome: DispatchOutcomeType = DispatchOutcomeType.EXPIRED,
    ) -> bool:
        """Purge a job whose payload is gone or whose wait deadline has expired.

        Clears pending/reserved membership, job payload, and dedupe key. Routes to
        the owning queue by namespace; a known-but-unregistered namespace is served
        by an ephemeral queue bound to that namespace so keys still target where
        the job actually lived. When the namespace cannot be resolved at all, the
        job is purged from every registered queue, but dedupe keys are deleted
        only in the namespaces where the job was actually found — never
        broadcast across all namespaces, so a stray orphan cannot break another
        queue's dedupe if ``task_key``/``work_item_id`` ever collide. Dedupe keys
        that cannot be attributed are left to expire by TTL.

        Idempotent under concurrent ZSCAN / finalize races: a second discard that
        finds nothing left in the zsets and no job payload skips outcome metrics.
        """
        resolved_task_key = task_key or resolve_task_key_from_job_id(
            job_id,
            _registered_task_keys(),
        )
        resolved_work_item_id = work_item_id
        job = queue_cls.get_job(job_id)
        if job:
            namespace = namespace or job.namespace
            resolved_task_key = resolved_task_key or job.task_key
            resolved_work_item_id = resolved_work_item_id or job.work_item_id
        if not resolved_work_item_id and resolved_task_key:
            resolved_work_item_id = work_item_id_from_job_id(job_id, resolved_task_key)
        try:
            target_queue = None
            if namespace:
                target_queue = queue_cls.queue_for_namespace(namespace) or queue_cls.ephemeral_queue_for_namespace(
                    namespace
                )
            pending_removed = 0
            reserved_removed = 0
            dedupe_namespaces = set()
            if target_queue is not None:
                pending_removed, reserved_removed = cls.purge_job(
                    target_queue,
                    job_id,
                    task_key=resolved_task_key,
                )
                dedupe_namespaces.add(target_queue.namespace)
            else:
                for candidate_queue in queue_cls.registered_queues():
                    pending_hit, reserved_hit = cls.purge_job(
                        candidate_queue,
                        job_id,
                        task_key=resolved_task_key,
                    )
                    pending_removed += pending_hit
                    reserved_removed += reserved_hit
                    if pending_hit > 0 or reserved_hit > 0:
                        dedupe_namespaces.add(candidate_queue.namespace)
            # Job payloads and dedupe keys are namespace-bound, so the
            # trailing cleanup is one pipeline per shard, grouped by the
            # namespaces actually hit. Never broadcast across all namespaces.
            delete_keys_by_ns: dict[str, list[str]] = {}
            if target_queue is not None:
                delete_keys_by_ns.setdefault(target_queue.namespace, []).append(target_queue.job_key(job_id))
            else:
                for ns in dedupe_namespaces:
                    delete_keys_by_ns.setdefault(ns, []).append(KEY_JOB_PREFIX.format(ns=ns) + job_id)
            if resolved_task_key and resolved_work_item_id:
                for ns in delete_keys_by_ns:
                    delete_keys_by_ns[ns].append(
                        DispatchQueue.dedupe_key_for_namespace(ns, resolved_task_key, resolved_work_item_id)
                    )
            job_deleted = False
            for ns, keys in delete_keys_by_ns.items():
                pipe = routing.conn_for_namespace(ns).pipeline(transaction=False)
                for key in keys:
                    pipe.delete(key)
                results = pipe.execute()
                if results and int(results[0] or 0) > 0:
                    job_deleted = True
            touched = pending_removed > 0 or reserved_removed > 0 or job_deleted
            if resolved_task_key and touched:
                outcome_queue = target_queue or queue_cls
                outcome_queue.record_outcome(resolved_task_key, outcome, worker_finished=False)
            if not touched:
                return True
        except Exception as exc:
            logger.warning("dispatch: discard_orphaned_job failed job_id=%s: %s", job_id, exc)
            return False
        log = logger.warning if outcome == DispatchOutcomeType.EXPIRED else logger.info
        log(
            "dispatch: discarded job_id=%s task_key=%s outcome=%s",
            job_id,
            resolved_task_key,
            outcome,
        )
        return True

    @classmethod
    def reap_orphaned_queue_jobs(
        cls,
        queue_cls: type[DispatchQueue],
        *,
        scan_limit: int = 200,
        deadline_at: Optional[float] = None,
    ) -> int:
        """Incrementally purge jobs whose payload TTL has expired.

        The ZSCAN cursor is persisted per zset across calls (see
        ``_reap_cursor_key``) so a scan truncated by ``scan_limit`` or the
        ``deadline_at`` budget resumes from where it stopped on the next tick
        instead of always revisiting the same leading buckets.
        """
        reaped = 0
        registered = _registered_task_keys()

        for key in (queue_cls.pending_key(), queue_cls.reserved_key()):
            cursor = cls._read_reap_cursor(queue_cls, key)
            scanned = 0
            try:
                while scanned < scan_limit:
                    if deadline_at is not None and time.monotonic() >= deadline_at:
                        cls._write_reap_cursor(queue_cls, key, cursor)
                        return reaped
                    cursor, members = queue_cls.conn().zscan(key, cursor, count=100)
                    job_ids = [decode_text(job_id) for job_id, _score in members[: max(0, scan_limit - scanned)]]
                    scanned += len(job_ids)
                    payloads = (
                        queue_cls.conn().mget([queue_cls.job_key(job_id) for job_id in job_ids]) if job_ids else []
                    )
                    orphan_ids = [job_id for job_id, payload in zip(job_ids, payloads) if not payload]
                    for job_id in orphan_ids:
                        task_key = resolve_task_key_from_job_id(job_id, registered)
                        if cls.discard_orphaned_job(
                            queue_cls,
                            job_id,
                            task_key=task_key,
                            namespace=queue_cls.namespace,
                            work_item_id=work_item_id_from_job_id(job_id, task_key),
                            outcome=DispatchOutcomeType.EXPIRED,
                        ):
                            reaped += 1
                    if cursor == 0:
                        cls._clear_reap_cursor(queue_cls, key)
                        break
                else:
                    # scan_limit reached mid-iteration: save the cursor so the
                    # next call resumes here instead of rescanning the head.
                    cls._write_reap_cursor(queue_cls, key, cursor)
            except Exception as exc:
                logger.warning("dispatch: reap_orphaned_queue_jobs failed key=%s: %s", key, exc)
        return reaped
