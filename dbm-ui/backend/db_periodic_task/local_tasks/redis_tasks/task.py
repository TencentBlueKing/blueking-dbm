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
import json
import logging
from typing import Optional

from celery.schedules import crontab

from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.scheduling import at_front, spread
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.check_backend_data_skew import (
    CheckBackendDataSkewTask,
)
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.check_backend_load_skew import (
    CheckBackendLoadSkewTask,
)
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.check_cluster_capacity_growth import (
    CheckClusterCapacityGrowthTask,
)
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import (
    REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE,
)
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter import RedisClusterSelector
from backend.db_periodic_task.local_tasks.redis_tasks.check_conf import check_redis_conf
from backend.db_periodic_task.local_tasks.redis_tasks.check_exporter import CheckRedisUpMetricTask
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_report.repo.task_record_repo import TaskRecordRepo
from backend.utils.redis import RedisConn

logger = logging.getLogger("celery")

"""
    To register a periodic task:
    1. Apply ``register_periodic_task``.
    2. Import the module from ``../__init__.py``.

    Redis LLM agent checks register via ``@ai_task`` on import of agent_checks.
    Producer beats run frequently but are cheap: a watermark HGET gates the
    rotation top-up, and the priority (alarm) lane is throttled to once/day.
"""

# ~1 day; the priority (alarm) lane runs at most once per this window per task.
_PRIORITY_PASS_TTL_SECONDS = 24 * 3600
_ROTATION_CURSOR_KEY = "redis_agent_check:rotation_cursor:{task_key}"
_PRIORITY_PASS_KEY = "redis_agent_check:priority_done:{task_key}"
# Daily alarm manifest + consumed-cursor keys. The manifest is the full alarm
# cluster snapshot for the day; each beat consumes up to ``available`` items and
# advances the cursor, so alarm clusters beyond one beat's capacity are not lost
# until the next day. Keys expire with the daily pass so a half-consumed day is
# superseded by the next day's fresh manifest.
_PRIORITY_MANIFEST_KEY = "redis_agent_check:priority_manifest:{task_key}"
_PRIORITY_CURSOR_KEY = "redis_agent_check:priority_cursor:{task_key}"
# Cap the daily manifest pull (bounded by the selector's 50-page pagination).
_PRIORITY_MANIFEST_MAX = 5000


def _read_rotation_cursor(task_key: str) -> int:
    try:
        return int(RedisConn.get(_ROTATION_CURSOR_KEY.format(task_key=task_key)) or 0)
    except Exception:
        return 0


def _write_rotation_cursor(task_key: str, cursor: int) -> None:
    try:
        RedisConn.set(_ROTATION_CURSOR_KEY.format(task_key=task_key), max(0, int(cursor)))
    except Exception as exc:
        logger.warning("%s: rotation cursor write failed: %s", task_key, exc)


def _try_claim_priority_pass(task_key: str) -> bool:
    """Atomically claim today's priority pass (SET NX). True => this worker runs it."""
    try:
        return bool(
            RedisConn.set(
                _PRIORITY_PASS_KEY.format(task_key=task_key),
                "1",
                nx=True,
                ex=_PRIORITY_PASS_TTL_SECONDS,
            )
        )
    except Exception as exc:
        logger.warning("%s: priority pass claim failed: %s", task_key, exc)
        return False


def _release_priority_pass(task_key: str) -> None:
    """Drop a claimed pass so the next beat can retry (select/filter/admission failure)."""
    try:
        RedisConn.delete(_PRIORITY_PASS_KEY.format(task_key=task_key))
    except Exception as exc:
        logger.warning("%s: priority pass release failed: %s", task_key, exc)


def _read_priority_manifest(task_key: str) -> Optional[list]:
    """Return the day's alarm manifest, or ``None`` when absent/unreadable.

    Unreadable counts as absent so the next beat rebuilds it (the pass claim is
    released separately if selection itself fails).
    """
    try:
        raw = RedisConn.get(_PRIORITY_MANIFEST_KEY.format(task_key=task_key))
    except Exception as exc:
        logger.warning("%s: priority manifest read failed: %s", task_key, exc)
        return None
    if not raw:
        return None
    try:
        manifest = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("%s: priority manifest unparseable, rebuild", task_key)
        return None
    return manifest if isinstance(manifest, list) else None


def _write_priority_manifest(task_key: str, items: list) -> None:
    try:
        RedisConn.set(
            _PRIORITY_MANIFEST_KEY.format(task_key=task_key),
            json.dumps(items, ensure_ascii=False),
            ex=_PRIORITY_PASS_TTL_SECONDS,
        )
    except Exception as exc:
        logger.warning("%s: priority manifest write failed: %s", task_key, exc)


def _clear_priority_manifest(task_key: str) -> None:
    try:
        RedisConn.delete(_PRIORITY_MANIFEST_KEY.format(task_key=task_key))
    except Exception as exc:
        logger.warning("%s: priority manifest clear failed: %s", task_key, exc)


def _read_priority_cursor(task_key: str) -> int:
    try:
        return int(RedisConn.get(_PRIORITY_CURSOR_KEY.format(task_key=task_key)) or 0)
    except Exception:
        return 0


def _write_priority_cursor(task_key: str, cursor: int) -> None:
    try:
        RedisConn.set(
            _PRIORITY_CURSOR_KEY.format(task_key=task_key),
            max(0, int(cursor)),
            ex=_PRIORITY_PASS_TTL_SECONDS,
        )
    except Exception as exc:
        logger.warning("%s: priority cursor write failed: %s", task_key, exc)


def _clear_priority_cursor(task_key: str) -> None:
    try:
        RedisConn.delete(_PRIORITY_CURSOR_KEY.format(task_key=task_key))
    except Exception as exc:
        logger.warning("%s: priority cursor clear failed: %s", task_key, exc)


def _count_enqueued(outcomes) -> int:
    return sum(1 for outcome in outcomes if outcome.outcome == DispatchOutcomeType.ENQUEUED)


def _has_retryable_enqueue_failure(outcomes) -> bool:
    """True when any outcome should hold produce cursors for a later retry.

    ``ENQUEUED`` / ``ENQUEUE_DUPLICATE`` are handled. ``ENQUEUE_DEADLINE_EXPIRED``
    is terminal (never retry), so it must not hold the cursor. Capacity,
    unavailable, and producer-gate rejects are temporary and must hold.
    """
    return any(
        outcome.outcome
        in {
            DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED,
            DispatchOutcomeType.ENQUEUE_UNAVAILABLE,
            DispatchOutcomeType.ENQUEUE_PRODUCER_PAUSED,
        }
        for outcome in outcomes
    )


def _available_admission_slots(task) -> int:
    """Return advisory shared-queue capacity; fail closed on unavailable state."""
    try:
        queue_config = task.queue_cls.load_config()
        pending = task.queue_cls.pending_count()
        reserved = task.queue_cls.reserved_count()
    except Exception as exc:
        logger.warning("%s: shared queue capacity query failed: %s", task.task_key, exc)
        return 0
    if pending < 0 or reserved < 0:
        logger.warning(
            "%s: shared queue capacity unavailable pending=%d reserved=%d",
            task.task_key,
            pending,
            reserved,
        )
        return 0
    return min(
        REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE,
        max(0, int(queue_config.max_admitted_jobs) - pending - reserved),
    )


def _produce_redis_agent_check(task_cls, *, filter_candidates=None):
    """Feed priority and rotation lanes.

    Alarm clusters jump the queue once daily. Rotation refills below the
    pending watermark, persists its cursor, and optionally spreads readiness.
    """
    task = task_cls()
    cfg = task.config
    if not cfg.enabled:
        return 0

    available = _available_admission_slots(task)
    if available <= 0:
        logger.debug("%s: producer skip, shared queue has no proven admission capacity", task.task_key)
        return 0

    selector = RedisClusterSelector(cfg, task.subtype, task_key=task.task_key)
    enqueued = 0

    # Lane 1: priority (alarm) clusters — at most once/day, jump the queue.
    # Claim the daily pass atomically (SET NX) so concurrent beats don't both run
    # the alarm query; release on select/filter failure so the next beat retries.
    # The first beat snapshots the full alarm manifest (not just ``available``
    # items); later beats consume it in chunks of ``available`` until it is fully
    # enqueued, so alarm clusters beyond one beat's capacity are still covered
    # today. The pass stays claimed until the whole manifest is consumed (or the
    # 24h TTL lapses and a fresh day begins).
    if _try_claim_priority_pass(task.task_key):
        manifest = _read_priority_manifest(task.task_key)
        if manifest is None:
            try:
                priority_items = selector.select_priority(limit=_PRIORITY_MANIFEST_MAX)
            except Exception:
                logger.exception("%s: priority alarm selection failed", task.task_key)
                _release_priority_pass(task.task_key)
            else:
                try:
                    if filter_candidates is not None:
                        priority_items = filter_candidates(priority_items)
                except Exception:
                    # Filter failure (e.g. dbconfig down): release the claim so the
                    # next beat retries, instead of silently skipping a day of alarm
                    # checks by holding a done marker on an empty outcome.
                    logger.exception("%s: priority candidate filter failed; hold for next beat", task.task_key)
                    _release_priority_pass(task.task_key)
                    return 0
                if priority_items:
                    _write_priority_manifest(task.task_key, priority_items)
                    _write_priority_cursor(task.task_key, 0)
                    manifest = priority_items

        if manifest is not None:
            cursor = _read_priority_cursor(task.task_key)
            pending_items = manifest[cursor:]
            if not pending_items:
                # Full manifest consumed: keep the daily pass claimed and drop
                # the manifest so the next day rebuilds from fresh alarms.
                _clear_priority_manifest(task.task_key)
                _clear_priority_cursor(task.task_key)
            else:
                lead = max(0, int(cfg.priority_execute_lead_seconds))
                batch = pending_items[:available]
                priority_outcomes = task.submit(batch, ready_at=at_front(lead))
                priority_enqueued = _count_enqueued(priority_outcomes)
                enqueued += priority_enqueued
                available = max(0, available - priority_enqueued)
                if _has_retryable_enqueue_failure(priority_outcomes):
                    # Hold the cursor: the same window is resubmitted next beat
                    # and dedupe blocks duplicates, so freed capacity is refilled
                    # immediately and no alarm cluster is skipped to the next day.
                    available = 0
                else:
                    # ENQUEUED and DUPLICATE both count as handled; advance past
                    # the whole batch so the manifest drains across beats.
                    next_cursor = cursor + len(batch)
                    if next_cursor >= len(manifest):
                        _clear_priority_manifest(task.task_key)
                        _clear_priority_cursor(task.task_key)
                    else:
                        _write_priority_cursor(task.task_key, next_cursor)

    # Lane 2: rotation top-up — watermark-gated on this task's own pending only.
    pending = task.pending_count
    low = max(1, int(cfg.produce_low_watermark))
    target = max(low, int(cfg.produce_target_pending))
    if pending >= 0 and pending < low and available > 0:
        budget = min(
            target - pending,
            available,
            REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE,
        )
        cursor = _read_rotation_cursor(task.task_key)
        rotation_items, next_cursor = selector.select_rotation(cursor=cursor, limit=budget)
        try:
            if filter_candidates is not None:
                rotation_items = filter_candidates(rotation_items)
        except Exception:
            # Same hold-and-retry rule as the priority lane: a filter failure
            # must not advance the cursor over unchecked clusters.
            logger.exception("%s: rotation candidate filter failed; hold cursor for next beat", task.task_key)
            return 0
        rotation_outcomes = []
        if rotation_items:
            window = max(0, int(cfg.produce_spread_window_seconds))
            rotation_outcomes = task.submit(rotation_items, ready_at=spread(window) if window > 0 else None)
            enqueued += _count_enqueued(rotation_outcomes)
        if not _has_retryable_enqueue_failure(rotation_outcomes):
            _write_rotation_cursor(task.task_key, next_cursor)
        # Retryable enqueue failures deliberately hold the cursor: the same
        # window is rescanned next beat and dedupe/watermark block duplicate
        # enqueues, so freed capacity / an open producer gate is refilled
        # immediately and no cluster is skipped to the next full rotation. The
        # cost is a repeated DB scan per beat while 0 < available < batch —
        # completeness beats scan efficiency here.

    logger.info("%s: produce_b pending=%d enqueued=%d", task.task_key, pending, enqueued)
    return enqueued


# Frequent beats are cheap above the watermark. Stagger checks to avoid
# simultaneous DB scans and queue refills; query alarms at most once daily.
@register_periodic_task(run_every=crontab(minute="1-59/10"))
def redis_cluster_capacity_growth_produce():
    from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.check_cluster_capacity_growth import (
        filter_produce_candidates,
    )

    return _produce_redis_agent_check(CheckClusterCapacityGrowthTask, filter_candidates=filter_produce_candidates)


@register_periodic_task(run_every=crontab(minute="4-59/10"))
def redis_backend_data_skew_produce():
    return _produce_redis_agent_check(CheckBackendDataSkewTask)


@register_periodic_task(run_every=crontab(minute="7-59/10"))
def redis_backend_load_skew_produce():
    return _produce_redis_agent_check(CheckBackendLoadSkewTask)


@register_periodic_task(run_every=crontab(minute=3, hour=2))
def redis_conf_check_task():
    """Redis unified conf check (role, predixy servers, etc.). Runs daily at 02:03."""
    check_redis_conf()


@register_periodic_task(run_every=crontab(minute=1, hour=8))
def redis_exporter_check_task():
    """Check Redis and proxy exporters for down, duplicate, or redundant metrics."""
    repo = TaskRecordRepo()
    repo.execute_task_with_record(
        db_type="redis",
        task_name="redis_exporter_check_task",
        task_type="exporter",
        check_task_instance=CheckRedisUpMetricTask(),
    )
