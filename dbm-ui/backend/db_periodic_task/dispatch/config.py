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

import dataclasses
import json
from dataclasses import dataclass, fields
from typing import ClassVar

from django.core.exceptions import ValidationError

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

DEFAULT_REQUEUE_COOLDOWN_SECONDS = 60
DEFAULT_MAX_REQUEUE_ATTEMPTS = 3
DEFAULT_QUEUE_WAIT_TTL_SECONDS = 24 * 3600
# How long an reserved job may occupy a concurrency slot before cleanup reclaims it.
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 3600
# Extra TTL after execution timeout so a finishing worker can still finalize.
RESERVED_TTL_MARGIN_SECONDS = 60
# How many jobs one admission / reservation EVAL may touch. Keeps each script
# short so other Redis clients are not blocked behind it.
DISPATCH_LUA_BATCH_SIZE = 25
PUMP_INTERVAL_SECONDS = 10
PUMP_DEADLINE_MARGIN_SECONDS = 2
# Lock must outlive the beat interval so a late/hung release cannot overlap the next tick.
PUMP_LOCK_MARGIN_SECONDS = 1
PUMP_CLEANUP_INTERVAL_SECONDS = 60
# The cleanup marker is a SET NX with a TTL, so a cold start writes every
# namespace's marker in the same tick and they then expire together. Spreading
# each namespace's period over [interval, interval * (1 + ratio)) decorrelates
# them, because a fleet-wide simultaneous reap roughly halves how many queues
# one tick can serve.
PUMP_CLEANUP_JITTER_RATIO = 0.5
# Full task_counts scans run outside the pump. Hard audits are daily; explicit
# drift requests are checked more frequently by the independent maintenance task.
TASK_COUNTS_REBUILD_FORCE_SECONDS = 24 * 3600
TASK_COUNTS_REBUILD_PERIOD_SECONDS = 10 * 60
TASK_COUNTS_REBUILD_RETRY_SECONDS = 3600
TASK_COUNTS_REBUILD_REQUEST_TTL_SECONDS = 2 * 24 * 3600
TASK_COUNTS_REBUILD_DEADLINE_SECONDS = 60
# Lock must outlive the scan deadline so two workers cannot overlap REPLACE.
TASK_COUNTS_REBUILD_LOCK_MARGIN_SECONDS = 60
TASK_COUNTS_REBUILD_LOCK_SECONDS = TASK_COUNTS_REBUILD_DEADLINE_SECONDS + TASK_COUNTS_REBUILD_LOCK_MARGIN_SECONDS
TASK_COUNTS_REBUILD_SCAN_COUNT = 500
TASK_COUNTS_REBUILD_SCAN_PAUSE_SECONDS = 0.005


class IdempotenceMode(StrStructuredEnum):
    """How ``submit()`` deduplicates work items at enqueue time.

    Item selection / producer-side pruning belongs before ``submit()``.
    """

    NONE = EnumField("none", "No enqueue dedupe")
    DEDUPE = EnumField(
        "dedupe",
        "Skip when work_item is pending, reserved, or has an active dedupe key",
    )


@dataclass
class DispatchPumpConfig:
    """Global controls for one pump tick.

    Pump-level knobs are process-global and stable, so they live as code
    defaults only; there is no DB override table for them. Per-queue behavior
    is tuned through ``DispatchQueueConfig`` (``DispatchQueueSettings``).
    """

    # Thread concurrency for one tick, and in practice the fan-out ceiling: the
    # pump can only service roughly
    #   0.8 * max_parallel_queues * deadline_seconds / per-queue pump_seconds
    # queues per tick, and a per-queue pump is ~12 serial Redis round trips.
    # Measured at 2ms Redis RTT: 4 threads stall at ~800 queues, 16 clears 2048
    # inside the deadline, 32 is still near-linear, 64 starts losing to
    # contention. Threads are created lazily per tick and capped by the queue
    # count, so a small fleet does not pay for a larger value.
    # See Notes/DispatchQueue/测试报告.md "多队列扇出".
    max_parallel_queues: int = 16

    @property
    def deadline_seconds(self) -> float:
        return float(PUMP_INTERVAL_SECONDS - PUMP_DEADLINE_MARGIN_SECONDS)

    @property
    def lock_ttl_seconds(self) -> int:
        return PUMP_INTERVAL_SECONDS + PUMP_LOCK_MARGIN_SECONDS


def _filter_raw_fields(config_cls, raw: dict) -> dict:
    valid_keys = {field.name for field in fields(config_cls)}
    return {key: value for key, value in (raw or {}).items() if key in valid_keys}


def _validate_raw_keys(config_cls, raw: dict):
    if not isinstance(raw, dict):
        raise ValidationError({"config": "must be a JSON object"})
    valid_keys = {field.name for field in fields(config_cls)}
    unknown = sorted(set(raw) - valid_keys)
    if unknown:
        raise ValidationError({"config": f"unknown fields: {', '.join(unknown)}"})
    try:
        return config_cls.from_raw(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"config": str(exc)}) from exc


def _validate_positive(config, *names: str) -> None:
    for name in names:
        if getattr(config, name) < 1:
            raise ValidationError({"config": f"{name} must be at least 1"})


@dataclass
class DispatchTaskConfig:
    """Effective runtime configuration for one registered dispatch task."""

    queue_namespace: ClassVar[str] = ""
    task_key: ClassVar[str] = ""
    enabled: bool = False
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE
    requeue_cooldown_seconds: int = DEFAULT_REQUEUE_COOLDOWN_SECONDS
    max_requeue_attempts: int = DEFAULT_MAX_REQUEUE_ATTEMPTS
    queue_wait_ttl_seconds: int = DEFAULT_QUEUE_WAIT_TTL_SECONDS
    execution_timeout_seconds: int = DEFAULT_EXECUTION_TIMEOUT_SECONDS

    def uses_enqueue_dedupe(self) -> bool:
        """Whether enqueue checks pending/reserved/dedupe key for the work_item."""
        return self.idempotence_mode == IdempotenceMode.DEDUPE

    def resolve_queue_wait_ttl_seconds(self) -> int:
        """Pending wait budget starting at max(enqueue time, ready_at)."""
        return max(1, int(self.queue_wait_ttl_seconds))

    def resolve_execution_timeout_seconds(self) -> int:
        """How long a reserved job may stay reserved before cleanup reclaims it."""
        return max(1, int(self.execution_timeout_seconds))

    def resolve_reserved_record_ttl_seconds(self) -> int:
        """Redis TTL for job/dedupe records while the job is reserved."""
        return self.resolve_execution_timeout_seconds() + RESERVED_TTL_MARGIN_SECONDS

    def to_raw(self) -> dict:
        data = dataclasses.asdict(self)
        data["idempotence_mode"] = self.idempotence_mode.value
        return data

    @classmethod
    def from_raw(cls, raw: dict):
        filtered = _filter_raw_fields(cls, raw)
        mode = filtered.get("idempotence_mode")
        if mode is not None and not isinstance(mode, IdempotenceMode):
            filtered["idempotence_mode"] = IdempotenceMode(mode)
        return cls(**filtered)

    @classmethod
    def from_json(cls, config_json: str):
        if not config_json:
            return cls()
        return cls.from_raw(json.loads(config_json))

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        config = _validate_raw_keys(cls, raw)
        _validate_positive(config, "queue_wait_ttl_seconds", "execution_timeout_seconds")
        if config.max_requeue_attempts < 0:
            raise ValidationError({"config": "max_requeue_attempts cannot be negative"})

    @classmethod
    def from_db(cls):
        from backend.db_periodic_task.dispatch.config_cache import DispatchSettingsCache

        if cls.task_key:
            return cls.from_raw(DispatchSettingsCache.get_task(cls.task_key))
        return cls()

    def save_to_db(self, *, user: str = "system") -> None:
        from backend.db_periodic_task.models import DispatchQueueSettings, DispatchTaskSettings

        if not self.queue_namespace or not self.task_key:
            raise ValueError("queue_namespace and task_key are required to persist dispatch task config")
        raw = self.to_raw()
        queue, _ = DispatchQueueSettings.objects.get_or_create(
            namespace=self.queue_namespace,
            defaults={"config": {}, "creator": user, "updater": user},
        )
        record, created = DispatchTaskSettings.objects.get_or_create(
            task_key=self.task_key,
            defaults={"queue": queue, "config": raw, "creator": user, "updater": user},
        )
        if not created:
            record.queue = queue
            record.config = raw
            record.updater = user
            record.save(update_fields=["queue", "config", "updater", "update_at"])


@dataclass
class DispatchQueueConfig:
    """Effective per-queue dispatch configuration.

    - ``max_admitted_jobs``: pending + reserved (enqueue gate)
    - ``max_reserved``: ceiling on concurrency slots held, counting jobs already
      reserved but not yet published to Celery; also the AIMD scale

    Queue/task producers should coalesce related work into bounded batches
    instead of continuously submitting fragmented work. ``max_reserved`` is
    the dominant driver of incremental Redis QPS (roughly linear), so the
    default stays conservative at 10; raise it only after load-testing Redis,
    Celery, and the downstream dependency together, and persist the override
    per namespace via ``DispatchQueueSettings``.
    """

    namespace: ClassVar[str] = ""
    max_admitted_jobs: int = 2000
    max_reserved: int = 10

    @classmethod
    def from_raw(cls, raw: dict):
        return cls(**_filter_raw_fields(cls, raw))

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        config = _validate_raw_keys(cls, raw)
        _validate_positive(
            config,
            "max_admitted_jobs",
            "max_reserved",
        )

    @classmethod
    def from_db(cls):
        from backend.db_periodic_task.dispatch.config_cache import DispatchSettingsCache

        return cls.from_raw(DispatchSettingsCache.get_queue(cls.namespace)) if cls.namespace else cls()

    def save_to_db(self, *, user: str = "system") -> None:
        from backend.db_periodic_task.models import DispatchQueueSettings

        if not self.namespace:
            raise ValueError("namespace is required to persist dispatch queue config")
        raw = dataclasses.asdict(self)
        record, created = DispatchQueueSettings.objects.get_or_create(
            namespace=self.namespace,
            defaults={"config": raw, "creator": user, "updater": user},
        )
        if not created:
            record.config = raw
            record.updater = user
            record.save(update_fields=["config", "updater", "update_at"])
