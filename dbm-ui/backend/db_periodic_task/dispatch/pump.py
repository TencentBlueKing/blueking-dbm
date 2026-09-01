# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import hashlib
import logging
import math
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.config import (
    DISPATCH_LUA_BATCH_SIZE,
    PUMP_CLEANUP_INTERVAL_SECONDS,
    PUMP_CLEANUP_JITTER_RATIO,
    PUMP_INTERVAL_SECONDS,
    DispatchPumpConfig,
    DispatchQueueConfig,
)
from backend.db_periodic_task.dispatch.controller import PumpControlDecision, PumpController
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.db_periodic_task.dispatch.lifecycle import QueueLifecycle
from backend.db_periodic_task.dispatch.lua import RELEASE_LOCK_LUA, compile_script, eval_script
from backend.db_periodic_task.dispatch.metrics import DispatchMetrics, decode_text, tick_id
from backend.db_periodic_task.dispatch.queue import DispatchQueue, try_acquire_ttl_gate
from backend.db_periodic_task.dispatch.reaper import OrphanReaper
from backend.db_periodic_task.dispatch.registry import dispatch_execute_job, register_failure_handlers
from backend.db_periodic_task.dispatch.reservation import BACKPRESSURE_STATUSES, QueueReservation, ReservationStatus
from backend.db_periodic_task.dispatch.task_counts import TaskCounts
from backend.db_periodic_task.register import register_periodic_task

logger = logging.getLogger("root")

PUMP_LOCK_KEY_PREFIX = "dispatch:{ns}:pump_lock"
PUMP_CLEANUP_KEY_PREFIX = "dispatch:{ns}:pump_cleanup"
# Occupies ``dispatch:{ns}:pump_lock`` so SET NX acquisition fails until resume / TTL.
PUMP_PAUSE_OWNER = "dispatch:paused"
# Pause/resume advances this baseline so intentional downtime is not counted as ``pump_ticks_skipped``.
PUMP_TICKS_SKIPPED_BASELINE_KEY_PREFIX = "dispatch:{ns}:pump_ticks_skipped_baseline"
PUMP_TICKS_SKIPPED_BASELINE_TTL_SECONDS = 24 * 3600
# Knuth multiplicative hash constant, used to scatter the per-tick pump order.
ROTATION_MULTIPLIER = 2654435761
# Ceiling on per-namespace ``pump_not_started`` writes in one tick. Deliberately
# small: this work happens *after* the deadline, and rotation means each tick
# starves a different set, so resolving every starved namespace's shard would
# keep paying cold route lookups and eat into ``PUMP_DEADLINE_MARGIN_SECONDS``.
# The warning log always carries the true total; the counters only need to name
# enough queues to point at the problem.
PUMP_STARVED_METRIC_LIMIT = 50

_release_lock_script = compile_script(RELEASE_LOCK_LUA)


def _pump_lock_key(namespace: str) -> str:
    return PUMP_LOCK_KEY_PREFIX.format(ns=namespace)


def _pump_ticks_skipped_baseline_key(namespace: str) -> str:
    return PUMP_TICKS_SKIPPED_BASELINE_KEY_PREFIX.format(ns=namespace)


def _mark_pump_ticks_skipped_baseline(namespace: str, *, current_tick: Optional[int] = None, client=None) -> None:
    """Ignore missed ticks at or before ``current_tick`` (pause / resume)."""
    try:
        client = client or routing.conn_for_namespace(namespace)
        client.set(
            _pump_ticks_skipped_baseline_key(namespace),
            int(tick_id() if current_tick is None else current_tick),
            ex=PUMP_TICKS_SKIPPED_BASELINE_TTL_SECONDS,
        )
    except Exception as exc:
        logger.debug("dispatch_global_pump[%s]: missed baseline write failed: %s", namespace, exc)


def _read_pump_ticks_skipped_baseline(namespace: str, *, client=None) -> int:
    try:
        raw = (client or routing.conn_for_namespace(namespace)).get(_pump_ticks_skipped_baseline_key(namespace))
    except Exception:
        return -1
    if raw is None:
        return -1
    try:
        return int(decode_text(raw))
    except (TypeError, ValueError):
        return -1


def _record_pump_ticks_skipped(queue_cls: type[DispatchQueue], current_tick_id: int, state: dict) -> int:
    """Backfill empty pump slots since the last decide (excluding pause windows)."""
    try:
        last_decide = int(state.get("tick_id", -1))
    except (TypeError, ValueError):
        last_decide = -1
    baseline = max(last_decide, _read_pump_ticks_skipped_baseline(queue_cls.namespace))
    if baseline < 0:
        return 0
    missed = max(0, int(current_tick_id) - baseline - 1)
    if missed:
        DispatchMetrics.record_queue_event(
            queue_cls.namespace,
            "pump_ticks_skipped",
            missed,
            timestamp=current_tick_id * PUMP_INTERVAL_SECONDS,
        )
        logger.info(
            "dispatch_global_pump[%s]: pump_ticks_skipped=%d current_tick=%d baseline=%d",
            queue_cls.namespace,
            missed,
            current_tick_id,
            baseline,
        )
    return missed


def pause_queue_pump(namespace: str, *, seconds: Optional[float] = None, alias: Optional[str] = None) -> dict:
    """Hold the per-namespace pump lock so ``dispatch_global_pump`` skips this queue.

    ``seconds=None`` keeps the pause until ``resume_queue_pump`` (no Redis TTL).
    Otherwise the pause auto-expires after ``ceil(seconds)`` (≥1).
    ``alias`` pins the Redis shard explicitly (used by remap so the pause lands
    on the old shard even while the route row is about to flip).
    """
    ns = namespace or ""
    if not ns:
        raise ValueError("namespace is required to pause a queue pump")
    key = _pump_lock_key(ns)
    client = routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)
    _mark_pump_ticks_skipped_baseline(ns, client=client)  # setting baseline here matters less than resuming pump
    if seconds is None:
        client.set(key, PUMP_PAUSE_OWNER)
        logger.warning("dispatch_global_pump[%s]: paused until resume", ns)
        return {"namespace": ns, "paused": True, "ttl_seconds": None}
    if float(seconds) <= 0:
        raise ValueError("seconds must be positive; use seconds=None to pause until resume")
    ttl = max(1, int(math.ceil(float(seconds))))
    client.set(key, PUMP_PAUSE_OWNER, ex=ttl)
    logger.warning("dispatch_global_pump[%s]: paused for %ss", ns, ttl)
    return {"namespace": ns, "paused": True, "ttl_seconds": ttl}


def resume_queue_pump(namespace: str, *, alias: Optional[str] = None) -> bool:
    """Clear a pause marker on the pump lock. Returns whether a pause key was removed."""
    ns = namespace or ""
    if not ns:
        raise ValueError("namespace is required to resume a queue pump")
    client = routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)
    removed = bool(
        eval_script(
            _release_lock_script,
            client=client,
            keys=[_pump_lock_key(ns)],
            args=[PUMP_PAUSE_OWNER],
        )
    )
    # Always advance baseline on resume so pause downtime is not counted as starvation.
    _mark_pump_ticks_skipped_baseline(ns, client=client)
    if removed:
        logger.warning("dispatch_global_pump[%s]: resumed", ns)
    return removed


def inspect_queue_pump_lock(namespace: str, *, alias: Optional[str] = None) -> dict:
    """Inspect who holds ``dispatch:{ns}:pump_lock``.

    Returns::

        {
            "namespace": "...",
            "key": "dispatch:{ns}:pump_lock",
            "held": bool,
            "owner": str | None,          # raw Redis value
            "state": "free" | "paused" | "pumping" | "held",
            "ttl_seconds": int | None,    # -1 = no expiry; None = missing
        }
    """
    ns = namespace or ""
    key = _pump_lock_key(ns) if ns else ""
    empty = {
        "namespace": ns,
        "key": key,
        "held": False,
        "owner": None,
        "state": "free",
        "ttl_seconds": None,
    }
    if not ns:
        return empty
    try:
        raw = (routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)).get(key)
    except Exception:
        return empty
    if raw is None:
        return empty
    owner = decode_text(raw)
    try:
        ttl = int((routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)).ttl(key))
    except Exception:
        ttl = None
    else:
        # redis: -2 = key missing (race)
        if ttl == -2:
            return empty
    if owner == PUMP_PAUSE_OWNER:
        state = "paused"
    elif owner.startswith("pump:"):
        state = "pumping"
    else:
        state = "held"
    return {
        "namespace": ns,
        "key": key,
        "held": True,
        "owner": owner,
        "state": state,
        "ttl_seconds": ttl,
    }


def is_queue_pump_paused(namespace: str, *, alias: Optional[str] = None) -> bool:
    """Whether the namespace pump lock is currently held by a pause marker."""
    return inspect_queue_pump_lock(namespace, alias=alias)["state"] == "paused"


def queue_pump_pause_ttl(namespace: str, *, alias: Optional[str] = None) -> Optional[int]:
    """Remaining pause TTL in seconds.

    ``None`` when not paused. ``-1`` when paused with no expiry (until resume).
    """
    info = inspect_queue_pump_lock(namespace, alias=alias)
    if info["state"] != "paused":
        return None
    return info["ttl_seconds"]


@dataclass
class _PumpTickStats:
    # How many ready job ids the peek returned (truncated at 3x the budget), the
    # closest available proxy for this tick's demand.
    ready_peeked: int = 0
    # Jobs newly promoted into the reserved set this tick.
    newly_reserved: int = 0
    published: int = 0
    blocked: int = 0
    missing: int = 0
    reserve_unavailable: int = 0
    publish_failed: int = 0
    queue_wait_samples: list[float] = field(default_factory=list)


def _cleanup_interval_for(namespace: str) -> int:
    """Per-namespace cleanup period, jittered to break fleet-wide alignment.

    The marker is a ``SET NX`` with a TTL, so a cold start writes every
    namespace's marker in the same tick and they all expire together — the whole
    fleet then reaps in lockstep every interval, and a reaping tick costs ~22
    Redis round trips instead of ~12, roughly halving how many queues one tick
    can serve. Deriving a stable offset from the namespace gives each queue its
    own period, so they decorrelate once and stay that way.
    """
    digest = hashlib.blake2s(namespace.encode("utf-8"), digest_size=4).digest()
    spread = max(1, int(PUMP_CLEANUP_INTERVAL_SECONDS * PUMP_CLEANUP_JITTER_RATIO))
    return PUMP_CLEANUP_INTERVAL_SECONDS + int.from_bytes(digest, "big") % spread


def _cleanup_due(queue_cls: type[DispatchQueue], interval_seconds: int) -> bool:
    return try_acquire_ttl_gate(
        PUMP_CLEANUP_KEY_PREFIX.format(ns=queue_cls.namespace),
        interval_seconds,
        client=queue_cls.conn(),
    )


def _maybe_cleanup_queue(queue_cls: type[DispatchQueue], deadline_at: float) -> None:
    """Run bounded cleanup and request any unbounded repair out of band."""
    if time.monotonic() >= deadline_at:
        return
    if not _cleanup_due(queue_cls, _cleanup_interval_for(queue_cls.namespace)):
        return
    orphaned = OrphanReaper.reap_orphaned_queue_jobs(queue_cls, deadline_at=deadline_at)
    if orphaned:
        logger.info("dispatch_global_pump[%s]: reaped_orphaned=%d", queue_cls.namespace, orphaned)
    if time.monotonic() >= deadline_at:
        logger.info("dispatch_global_pump[%s]: cleanup hit deadline, skip drift check", queue_cls.namespace)
        return
    drifted = TaskCounts.counts_drifted(queue_cls)
    if orphaned or drifted:
        reason = "orphaned" if orphaned else "count_drift"
        TaskCounts.request_rebuild(queue_cls, reason)


def _hydrate_and_drop_stale(
    queue_cls: type[DispatchQueue],
    job_ids: list[str],
    budget: int,
) -> tuple[list[DispatchJob], int]:
    """Hydrate peeked jobs, discard missing/expired ones, trim to budget."""
    jobs = queue_cls.get_jobs(job_ids)
    hydrated: list[DispatchJob] = []
    missing_count = 0
    now = time.time()
    for job_id in job_ids:
        job = jobs.get(job_id)
        if not job:
            missing_count += 1
            OrphanReaper.discard_orphaned_job(queue_cls, job_id, namespace=queue_cls.namespace)
            continue
        if job.wait_deadline_at and job.wait_deadline_at <= now:
            OrphanReaper.discard_orphaned_job(
                queue_cls,
                job_id,
                task_key=job.task_key,
                namespace=queue_cls.namespace,
            )
            continue
        hydrated.append(job)
    return hydrated[:budget], missing_count


def _requeue_reserved_tail(
    queue_cls: type[DispatchQueue],
    chunk: list[DispatchJob],
    statuses: list[ReservationStatus],
    from_index: int,
) -> None:
    for pending_job, pending_status in zip(chunk[from_index:], statuses[from_index:]):
        if pending_status == ReservationStatus.RESERVED:
            QueueLifecycle.requeue(
                queue_cls=queue_cls,
                job=pending_job,
                ready_at=pending_job.ready_at,
                queue_wait_ttl=queue_cls.resolve_queue_wait_ttl_from_job(pending_job),
            )


def _reserve_and_publish(
    queue_cls: type[DispatchQueue],
    jobs: list[DispatchJob],
    config: DispatchQueueConfig,
    decision: PumpControlDecision,
    deadline_at: float,
    current_tick_id: int,
    stats: _PumpTickStats,
) -> None:
    """Reserve and Celery-publish jobs until blocked, deadline, or publish failure."""
    blocked = False
    reserved_record_ttl_cache: dict[tuple[str, str], int] = {}
    for offset in range(0, len(jobs), DISPATCH_LUA_BATCH_SIZE):
        if blocked or time.monotonic() >= deadline_at:
            break
        chunk = jobs[offset : offset + DISPATCH_LUA_BATCH_SIZE]
        reserved_record_ttls = []
        for job in chunk:
            config_identity = (job.task_key, job.config_json)
            if config_identity not in reserved_record_ttl_cache:
                reserved_record_ttl_cache[config_identity] = queue_cls.resolve_reserved_record_ttl_from_job(job)
            reserved_record_ttls.append(reserved_record_ttl_cache[config_identity])
        statuses = QueueReservation.reserve_jobs(
            chunk,
            config,
            queue_cls=queue_cls,
            reserved_record_ttls=reserved_record_ttls,
            tick_id=current_tick_id,
            tick_budget=decision.effective_budget,
        )
        stats.newly_reserved += sum(status == ReservationStatus.RESERVED for status in statuses)
        stats.blocked += sum(status in BACKPRESSURE_STATUSES for status in statuses)
        stats.missing += sum(status == ReservationStatus.MISSING for status in statuses)
        unavailable = sum(status == ReservationStatus.UNAVAILABLE for status in statuses)
        if unavailable:
            stats.reserve_unavailable += unavailable
            logger.warning(
                "dispatch_global_pump[%s]: reserve unavailable count=%d",
                queue_cls.namespace,
                unavailable,
            )

        for index, (job, status) in enumerate(zip(chunk, statuses)):
            if status == ReservationStatus.MISSING:
                continue
            if status != ReservationStatus.RESERVED:
                # Backpressure or a dead EVAL: either way stop pumping this tick.
                blocked = True
                continue
            became_ready_at = max(job.created_at, job.ready_at)
            stats.queue_wait_samples.append(max(0.0, time.time() - became_ready_at))
            try:
                dispatch_execute_job.apply_async(args=[job.job_id])
            except Exception as exc:
                stats.publish_failed += 1
                _requeue_reserved_tail(queue_cls, chunk, statuses, index)
                logger.warning(
                    "dispatch_global_pump[%s]: publish failed job_id=%s: %s",
                    queue_cls.namespace,
                    job.job_id,
                    exc,
                )
                return
            stats.published += 1


def _flush_pump_metrics(
    queue_cls: type[DispatchQueue],
    stats: _PumpTickStats,
    metric_timestamp: float,
    started_at: float,
) -> None:
    try:
        pipe = queue_cls.conn().pipeline(transaction=False)
        for name, amount in (
            ("ready_peeked", stats.ready_peeked),
            ("reserved", stats.newly_reserved),
            ("published", stats.published),
            ("blocked", stats.blocked),
            ("missing", stats.missing),
            ("reserve_unavailable", stats.reserve_unavailable),
            ("publish_failed", stats.publish_failed),
        ):
            if amount:
                DispatchMetrics.record_queue_event(
                    queue_cls.namespace,
                    name,
                    amount,
                    timestamp=metric_timestamp,
                    client=pipe,
                )
        DispatchMetrics.record_histogram_values(
            queue_cls.namespace,
            "queue_wait_seconds",
            stats.queue_wait_samples,
            timestamp=metric_timestamp,
            client=pipe,
        )
        DispatchMetrics.record_histogram(
            queue_cls.namespace,
            "pump_seconds",
            time.monotonic() - started_at,
            client=pipe,
        )
        pipe.execute()
    except Exception as exc:
        logger.debug("dispatch_global_pump[%s]: metrics flush failed: %s", queue_cls.namespace, exc)


def _pump_queue(queue_cls: type[DispatchQueue], deadline_at: float, current_tick_id: int) -> int:
    """Drain one queue earliest-ready-first, up to its tick budget and the deadline."""
    started_at = time.monotonic()
    metric_timestamp = current_tick_id * PUMP_INTERVAL_SECONDS
    stats = _PumpTickStats()
    if time.monotonic() >= deadline_at:
        return 0
    config = queue_cls.load_config()
    _maybe_cleanup_queue(queue_cls, deadline_at)
    # One read of the controller hash serves both the starvation backfill and the
    # budget decision; they used to HGETALL the same key twice per tick.
    controller_state = PumpController.read_state(queue_cls.namespace)
    _record_pump_ticks_skipped(queue_cls, current_tick_id, controller_state)

    try:
        decision = PumpController.decide(queue_cls, config, current_tick_id=current_tick_id, state=controller_state)
        if decision.effective_budget <= 0:
            return 0
        job_ids = queue_cls.peek_ready(max(10, decision.effective_budget * 3))
        stats.ready_peeked = len(job_ids)
        if not job_ids:
            return 0
        jobs, missing = _hydrate_and_drop_stale(queue_cls, job_ids, decision.effective_budget)
        stats.missing = missing
        _reserve_and_publish(queue_cls, jobs, config, decision, deadline_at, current_tick_id, stats)
        logger.info(
            "dispatch_global_pump[%s]: ready_peeked=%d budget=%d cwnd=%d slots=%d published=%d aimd=%s",
            queue_cls.namespace,
            stats.ready_peeked,
            decision.effective_budget,
            decision.congestion_window,
            decision.available_slots,
            stats.published,
            decision.aimd_action,
        )
        return stats.published
    finally:
        _flush_pump_metrics(queue_cls, stats, metric_timestamp, started_at)


def _try_acquire_pump_lock(namespace: str, owner: str, ttl_seconds: int) -> bool:
    try:
        return bool(
            routing.conn_for_namespace(namespace).set(
                _pump_lock_key(namespace),
                owner,
                nx=True,
                ex=max(1, int(ttl_seconds)),
            )
        )
    except Exception as exc:
        logger.warning("dispatch_global_pump[%s]: lock acquisition failed: %s", namespace, exc)
        return False


def _release_pump_lock(namespace: str, owner: str) -> None:
    try:
        eval_script(
            _release_lock_script,
            client=routing.conn_for_namespace(namespace),
            keys=[_pump_lock_key(namespace)],
            args=[owner],
        )
    except Exception as exc:
        logger.warning("dispatch_global_pump[%s]: lock release failed: %s", namespace, exc)


def _pump_queue_with_lock(
    queue_cls: type[DispatchQueue],
    deadline_at: float,
    current_tick_id: int,
    lock_ttl_seconds: int,
) -> int:
    """Acquire the per-namespace pump lock, then drain that queue once."""
    owner = f"pump:{queue_cls.namespace}:{uuid.uuid4().hex}"
    if not _try_acquire_pump_lock(queue_cls.namespace, owner, lock_ttl_seconds):
        if is_queue_pump_paused(queue_cls.namespace):
            logger.info("dispatch_global_pump[%s]: paused, skip", queue_cls.namespace)
        else:
            logger.debug("dispatch_global_pump[%s]: lock contention, skip", queue_cls.namespace)
            DispatchMetrics.record_queue_event(
                queue_cls.namespace,
                "pump_lock_contention",
                timestamp=current_tick_id * PUMP_INTERVAL_SECONDS,
            )
        return 0
    try:
        return _pump_queue(queue_cls, deadline_at, current_tick_id)
    finally:
        _release_pump_lock(queue_cls.namespace, owner)


def _rotate_for_tick(
    queues: list[type[DispatchQueue]],
    current_tick_id: int,
) -> list[type[DispatchQueue]]:
    """Rotate the pump order so an over-wide fleet degrades fairly.

    ``registered_queues()`` returns registry insertion order, which is stable, so a
    fleet the deadline cannot finish would otherwise starve the exact same tail
    on every tick — permanently, and silently. Offsetting the start makes the
    served window slide, so every queue is reached within a few ticks.

    The offset is a multiplicative hash of the tick id rather than the tick id
    itself: stepping by one would take one tick per queue to work through a wide
    fleet, whereas scattering the start covers everything in a handful of ticks.
    It stays a pure function of the tick, so multiple workers pumping the same
    tick agree on the order and the namespace locks still dedupe cleanly.
    """
    if len(queues) < 2:
        return queues
    offset = (int(current_tick_id) * ROTATION_MULTIPLIER) % len(queues)
    return queues[offset:] + queues[:offset]


def _record_pump_not_started(queues: list[type[DispatchQueue]], current_tick_id: int) -> None:
    """Flag queues the tick deadline never let us submit.

    Without this, a fleet wider than one tick can service is invisible: a starved
    queue never enters ``_pump_queue``, so it records neither ``pump_ticks_skipped`` nor
    anything else and looks exactly like an idle queue, while its pending set
    grows until ``max_admitted_jobs`` starts rejecting producers.

    Writes are grouped one pipeline per shard and capped, so an oversized fleet
    cannot turn its own diagnosis into a write storm; the rotation means the cap
    still covers every starved queue across consecutive ticks.
    """
    if not queues:
        return
    logger.warning(
        "dispatch_global_pump: deadline starved %d queues tick=%d head=%s",
        len(queues),
        current_tick_id,
        ",".join(queue_cls.namespace for queue_cls in queues[:5]),
    )
    timestamp = current_tick_id * PUMP_INTERVAL_SECONDS
    # Group by shard connection, resolved through the memoized helper: this runs
    # after the deadline has already passed, and ``resolve_alias`` would re-read
    # the whole route map once per namespace.
    by_shard: dict[int, tuple[object, list[str]]] = {}
    for queue_cls in queues[:PUMP_STARVED_METRIC_LIMIT]:
        try:
            client = routing.conn_for_namespace(queue_cls.namespace)
        except Exception:
            continue
        by_shard.setdefault(id(client), (client, []))[1].append(queue_cls.namespace)
    for client, namespaces in by_shard.values():
        try:
            pipe = client.pipeline(transaction=False)
            for namespace in namespaces:
                DispatchMetrics.record_queue_event(
                    namespace,
                    "pump_not_started",
                    timestamp=timestamp,
                    client=pipe,
                )
            pipe.execute()
        except Exception as exc:
            logger.debug("dispatch_global_pump: pump_not_started flush failed: %s", exc)


@register_periodic_task(run_every=timedelta(seconds=PUMP_INTERVAL_SECONDS))
def dispatch_global_pump():
    """Drain registered queues with per-namespace locks.

    Each Celery worker may pump different namespaces in the same tick. The lock
    is namespace-scoped so multi-worker fleets actually parallelize across queues;
    ``max_parallel_queues`` only caps in-process thread concurrency.

    There is no explicit cap on queues per tick: the deadline is the cap. Queues
    the deadline leaves unsubmitted are reported through ``pump_not_started``.
    """
    queues = DispatchQueue.registered_queues()
    if not queues:
        return 0
    pump_config = DispatchPumpConfig()
    current_tick_id = tick_id()
    queues = _rotate_for_tick(queues, current_tick_id)
    deadline_at = time.monotonic() + pump_config.deadline_seconds
    lock_ttl_seconds = pump_config.lock_ttl_seconds
    total = 0
    worker_count = min(len(queues), max(1, int(pump_config.max_parallel_queues)))
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="dispatch-pump") as executor:
        queue_iter = iter(queues)
        futures = {}

        def submit_next() -> bool:
            if time.monotonic() >= deadline_at:
                return False
            try:
                queue_cls = next(queue_iter)
            except StopIteration:
                return False
            futures[
                executor.submit(
                    _pump_queue_with_lock,
                    queue_cls,
                    deadline_at,
                    current_tick_id,
                    lock_ttl_seconds,
                )
            ] = queue_cls
            return True

        for _ in range(worker_count):
            if not submit_next():
                break
        while futures:
            completed, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in completed:
                queue_cls = futures.pop(future)
                try:
                    total += future.result()
                except Exception as exc:
                    logger.warning("dispatch_global_pump[%s]: failed: %s", queue_cls.namespace, exc)
                submit_next()
        # Whatever the iterator still holds is what the deadline refused.
        _record_pump_not_started(list(queue_iter), current_tick_id)
    return total


register_failure_handlers()
