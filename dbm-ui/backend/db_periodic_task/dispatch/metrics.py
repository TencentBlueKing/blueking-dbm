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

import bisect
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.config import PUMP_INTERVAL_SECONDS
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType

logger = logging.getLogger("root")

HOUR_SECONDS = 60 * 60
# AIMD only reads the previous closed tick. Two hours cover an hour boundary and
# leave enough time for delayed diagnostics without retaining a monitoring window.
TICK_RETENTION_SECONDS = 2 * HOUR_SECONDS
# Task keys are the only cumulative family whose cardinality follows registrations.
# Idle expiry bounds retired tasks; Prometheus treats a later reappearance as reset.
TASK_METRICS_IDLE_TTL_SECONDS = 30 * 24 * HOUR_SECONDS

KEY_TICK_METRICS_PREFIX = "dispatch:{ns}:metrics:tick:"
KEY_QUEUE_EVENTS = "dispatch:{ns}:metrics:cumulative:events"
KEY_TASK_OUTCOMES_PREFIX = "dispatch:{ns}:metrics:cumulative:task:"
KEY_HISTOGRAMS = "dispatch:{ns}:metrics:cumulative:histograms"
KEY_METRICS_STARTED_AT = "dispatch:{ns}:metrics:cumulative:started_at"

QUEUE_EVENT_NAMES = (
    "enqueued",
    "ready_peeked",
    "reserved",
    "published",
    "worker_finished",
    "enqueue_duplicate",
    "enqueue_capacity_rejected",
    "enqueue_producer_paused",
    "enqueue_deadline_expired",
    "enqueue_unavailable",
    "blocked",
    "congestion",
    "missing",
    "reserve_unavailable",
    "publish_failed",
    "celery_failure",
    "pump_ticks_skipped",
    "pump_lock_contention",
    "pump_not_started",
)
QUEUE_EVENT_NAME_SET = frozenset(QUEUE_EVENT_NAMES)

TASK_OUTCOME_NAMES = tuple(outcome.value for outcome in DispatchOutcomeType)
TASK_OUTCOME_NAME_SET = frozenset(TASK_OUTCOME_NAMES)

# Only these counters are control-plane inputs. Everything else is cumulative
# observability state and does not need a per-tick copy.
AIMD_TICK_COUNTER_NAMES = (
    "published",
    "worker_finished",
    "ready_peeked",
    "congestion",
    "blocked",
    "publish_failed",
)

# Stage-specific, code-owned classic-histogram boundaries. Changing a boundary
# requires a new metric name because old and new `le` series are not mergeable.
HISTOGRAM_BUCKETS: dict[str, tuple[float, ...]] = {
    "queue_wait_seconds": (
        0.1,
        0.5,
        1.0,
        5.0,
        10.0,
        30.0,
        60.0,
        300.0,
        600.0,
        1800.0,
        3600.0,
        21600.0,
        86400.0,
        math.inf,
    ),
    "execution_seconds": (
        0.01,
        0.05,
        0.1,
        0.5,
        1.0,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
        300.0,
        600.0,
        1800.0,
        3600.0,
        math.inf,
    ),
    "pump_seconds": (
        0.001,
        0.005,
        0.01,
        0.05,
        0.1,
        0.5,
        1.0,
        2.0,
        4.0,
        6.0,
        8.0,
        10.0,
        math.inf,
    ),
}
HISTOGRAM_STAGES = tuple(HISTOGRAM_BUCKETS)

RECORD_QUEUE_EVENT_LUA = """
redis.call('SET', KEYS[3], ARGV[5], 'NX')
local value = redis.call('HINCRBY', KEYS[1], ARGV[1], ARGV[2])
if ARGV[3] ~= '' then
    redis.call('HINCRBY', KEYS[2], ARGV[3], ARGV[2])
    redis.call('EXPIRE', KEYS[2], ARGV[4])
end
return value
"""

RECORD_TASK_OUTCOME_LUA = """
redis.call('SET', KEYS[2], ARGV[4], 'NX')
local value = redis.call('HINCRBY', KEYS[1], ARGV[1], ARGV[2])
redis.call('EXPIRE', KEYS[1], ARGV[3])
return value
"""

RECORD_HISTOGRAM_LUA = """
redis.call('SET', KEYS[2], ARGV[4], 'NX')
local stage = ARGV[1]
local observation_count = tonumber(ARGV[2])
local observation_sum = ARGV[3]
redis.call('HINCRBY', KEYS[1], stage .. ':count', observation_count)
redis.call('HINCRBYFLOAT', KEYS[1], stage .. ':sum', observation_sum)
local pair_count = tonumber(ARGV[5])
for index = 1, pair_count do
    local offset = 5 + ((index - 1) * 2)
    local bin_index = ARGV[offset + 1]
    local bin_count = ARGV[offset + 2]
    redis.call('HINCRBY', KEYS[1], stage .. ':bin:' .. bin_index, bin_count)
end
return observation_count
"""


def decode_text(value) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def tick_id(timestamp: Optional[float] = None) -> int:
    return int((time.time() if timestamp is None else timestamp) // PUMP_INTERVAL_SECONDS)


def _hour_id(timestamp: float) -> int:
    return int(timestamp // HOUR_SECONDS)


def _tick_key(namespace: str, hour_id: int) -> str:
    return f"{KEY_TICK_METRICS_PREFIX.format(ns=namespace)}{hour_id}"


def _queue_events_key(namespace: str) -> str:
    return KEY_QUEUE_EVENTS.format(ns=namespace)


def _task_outcomes_key(namespace: str, task_key: str) -> str:
    return f"{KEY_TASK_OUTCOMES_PREFIX.format(ns=namespace)}{task_key}"


def _histograms_key(namespace: str) -> str:
    return KEY_HISTOGRAMS.format(ns=namespace)


def _started_at_key(namespace: str) -> str:
    return KEY_METRICS_STARTED_AT.format(ns=namespace)


def _tick_field(timestamp: float, name: str) -> str:
    second_in_hour = int(timestamp) % HOUR_SECONDS
    return f"t:{second_in_hour // PUMP_INTERVAL_SECONDS}:{name}"


def _bucket_label(boundary: float) -> str:
    return "+Inf" if math.isinf(boundary) else format(boundary, "g")


def _decode_mapping(raw: dict) -> dict[str, str]:
    return {decode_text(key): decode_text(value) for key, value in raw.items()}


@dataclass
class HistogramSummary:
    buckets: list[tuple[str, int]] = field(default_factory=list)
    count: int = 0
    sum: float = 0.0


class DispatchMetrics:
    """Fail-open cumulative metrics plus short-lived AIMD tick counters."""

    _queue_event_script = None
    _task_outcome_script = None
    _histogram_script = None

    @classmethod
    def _get_queue_event_script(cls):
        if cls._queue_event_script is None:
            cls._queue_event_script = compile_script(RECORD_QUEUE_EVENT_LUA)
        return cls._queue_event_script

    @classmethod
    def _get_task_outcome_script(cls):
        if cls._task_outcome_script is None:
            cls._task_outcome_script = compile_script(RECORD_TASK_OUTCOME_LUA)
        return cls._task_outcome_script

    @classmethod
    def _get_histogram_script(cls):
        if cls._histogram_script is None:
            cls._histogram_script = compile_script(RECORD_HISTOGRAM_LUA)
        return cls._histogram_script

    @classmethod
    def enqueue_counter_spec(
        cls,
        namespace: str,
        task_key: str,
        *,
        timestamp: Optional[float] = None,
    ) -> tuple[str, str, str, int, float]:
        """Return cumulative keys/metadata for atomic admission metrics."""
        observed_at = time.time() if timestamp is None else float(timestamp)
        return (
            _task_outcomes_key(namespace, task_key),
            _queue_events_key(namespace),
            _started_at_key(namespace),
            TASK_METRICS_IDLE_TTL_SECONDS,
            observed_at,
        )

    @classmethod
    def record_queue_event(
        cls,
        namespace: str,
        name: str,
        amount: int = 1,
        *,
        timestamp: Optional[float] = None,
        client=None,
    ) -> None:
        if name not in QUEUE_EVENT_NAME_SET or not amount:
            return
        observed_at = time.time() if timestamp is None else float(timestamp)
        tick_field = _tick_field(observed_at, name) if name in AIMD_TICK_COUNTER_NAMES else ""
        try:
            client = client or routing.conn_for_namespace(namespace)
            eval_script(
                cls._get_queue_event_script(),
                client=client,
                keys=[
                    _queue_events_key(namespace),
                    _tick_key(namespace, _hour_id(observed_at)),
                    _started_at_key(namespace),
                ],
                args=[name, int(amount), tick_field, TICK_RETENTION_SECONDS, observed_at],
            )
        except Exception as exc:
            logger.debug("dispatch metrics: queue event failed namespace=%s name=%s: %s", namespace, name, exc)

    @classmethod
    def record_task_event(
        cls,
        namespace: str,
        task_key: str,
        name: str,
        amount: int = 1,
        *,
        timestamp: Optional[float] = None,
        client=None,
    ) -> None:
        if name not in TASK_OUTCOME_NAME_SET or not amount:
            return
        observed_at = time.time() if timestamp is None else float(timestamp)
        try:
            client = client or routing.conn_for_namespace(namespace)
            eval_script(
                cls._get_task_outcome_script(),
                client=client,
                keys=[_task_outcomes_key(namespace, task_key), _started_at_key(namespace)],
                args=[name, int(amount), TASK_METRICS_IDLE_TTL_SECONDS, observed_at],
            )
        except Exception as exc:
            logger.debug("dispatch metrics: task outcome failed task_key=%s name=%s: %s", task_key, name, exc)

    @classmethod
    def record_enqueue_outcome(cls, namespace: str, task_key: str, name: str, amount: int = 1) -> None:
        """Record a producer outcome when admission Lua could not self-report."""
        try:
            pipe = routing.conn_for_namespace(namespace).pipeline(transaction=False)
            cls.record_task_event(namespace, task_key, name, amount=amount, client=pipe)
            cls.record_queue_event(namespace, name, amount=amount, client=pipe)
            pipe.execute()
        except Exception as exc:
            logger.debug("dispatch metrics: enqueue outcome failed task_key=%s name=%s: %s", task_key, name, exc)

    @classmethod
    def record_histogram(
        cls,
        namespace: str,
        stage: str,
        value: float,
        *,
        timestamp: Optional[float] = None,
        client=None,
    ) -> None:
        cls.record_histogram_values(
            namespace,
            stage,
            [value],
            timestamp=timestamp,
            client=client,
        )

    @classmethod
    def record_histogram_values(
        cls,
        namespace: str,
        stage: str,
        values: Iterable[float],
        *,
        timestamp: Optional[float] = None,
        client=None,
    ) -> None:
        boundaries = HISTOGRAM_BUCKETS.get(stage)
        if boundaries is None:
            return
        valid: list[float] = []
        for raw_value in values:
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value >= 0:
                valid.append(value)
        if not valid:
            return
        bin_counts: dict[int, int] = {}
        for value in valid:
            index = bisect.bisect_left(boundaries, value)
            bin_counts[index] = bin_counts.get(index, 0) + 1
        observed_at = time.time() if timestamp is None else float(timestamp)
        args: list[object] = [stage, len(valid), sum(valid), observed_at, len(bin_counts)]
        for index, count in sorted(bin_counts.items()):
            args.extend([index, count])
        try:
            client = client or routing.conn_for_namespace(namespace)
            eval_script(
                cls._get_histogram_script(),
                client=client,
                keys=[_histograms_key(namespace), _started_at_key(namespace)],
                args=args,
            )
        except Exception as exc:
            logger.debug("dispatch metrics: histogram failed namespace=%s stage=%s: %s", namespace, stage, exc)

    @classmethod
    def record_task_outcome(
        cls,
        namespace: str,
        task_key: str,
        outcome: DispatchOutcomeType,
        *,
        elapsed_seconds: float = -1.0,
        worker_finished: bool = True,
        congested: bool = False,
        timestamp: Optional[float] = None,
    ) -> None:
        observed_at = time.time() if timestamp is None else float(timestamp)
        try:
            pipe = routing.conn_for_namespace(namespace).pipeline(transaction=False)
            cls.record_task_event(
                namespace,
                task_key,
                outcome.value,
                timestamp=observed_at,
                client=pipe,
            )
            if worker_finished:
                cls.record_queue_event(namespace, "worker_finished", timestamp=observed_at, client=pipe)
            if congested:
                cls.record_queue_event(namespace, "congestion", timestamp=observed_at, client=pipe)
            if elapsed_seconds >= 0:
                cls.record_histogram(
                    namespace,
                    "execution_seconds",
                    elapsed_seconds,
                    timestamp=observed_at,
                    client=pipe,
                )
            pipe.execute()
        except Exception as exc:
            logger.debug("dispatch metrics: outcome failed task_key=%s outcome=%s: %s", task_key, outcome, exc)

    @classmethod
    def queue_tick_counts(
        cls,
        namespace: str,
        observed_tick_id: int,
        *,
        names: Iterable[str] = AIMD_TICK_COUNTER_NAMES,
    ) -> dict[str, int]:
        """Point-read one short-lived tick via HMGET."""
        timestamp = observed_tick_id * PUMP_INTERVAL_SECONDS
        field_names = tuple(name for name in names if name in AIMD_TICK_COUNTER_NAMES)
        if not field_names:
            return {}
        redis_fields = [_tick_field(timestamp, name) for name in field_names]
        values = (
            routing.conn_for_namespace(namespace).hmget(
                _tick_key(namespace, _hour_id(timestamp)),
                redis_fields,
            )
            or []
        )
        result: dict[str, int] = {}
        for name, raw_value in zip(field_names, values):
            if raw_value is not None:
                result[name] = int(decode_text(raw_value))
        return result

    @classmethod
    def read_queue_events(cls, namespace: str) -> dict[str, int]:
        raw = _decode_mapping(routing.conn_for_namespace(namespace).hgetall(_queue_events_key(namespace)) or {})
        return {name: int(raw.get(name, 0) or 0) for name in QUEUE_EVENT_NAMES}

    @classmethod
    def read_task_outcomes(cls, namespace: str, task_key: str) -> dict[str, int]:
        raw = _decode_mapping(
            routing.conn_for_namespace(namespace).hgetall(_task_outcomes_key(namespace, task_key)) or {}
        )
        return {name: int(raw.get(name, 0) or 0) for name in TASK_OUTCOME_NAMES}

    @classmethod
    def read_histograms(cls, namespace: str) -> dict[str, HistogramSummary]:
        raw = _decode_mapping(routing.conn_for_namespace(namespace).hgetall(_histograms_key(namespace)) or {})
        result: dict[str, HistogramSummary] = {}
        for stage, boundaries in HISTOGRAM_BUCKETS.items():
            running = 0
            buckets: list[tuple[str, int]] = []
            for index, boundary in enumerate(boundaries):
                running += int(raw.get(f"{stage}:bin:{index}", 0) or 0)
                buckets.append((_bucket_label(boundary), running))
            count = int(raw.get(f"{stage}:count", 0) or 0)
            result[stage] = HistogramSummary(
                buckets=buckets,
                count=count,
                sum=float(raw.get(f"{stage}:sum", 0.0) or 0.0),
            )
        return result

    @classmethod
    def read_started_at(cls, namespace: str) -> Optional[float]:
        raw = routing.conn_for_namespace(namespace).get(_started_at_key(namespace))
        return None if raw is None else float(decode_text(raw))
