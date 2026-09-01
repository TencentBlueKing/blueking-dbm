# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Enqueue-time helpers for ``DispatchTask.submit(..., ready_at=...)``.

Pending is a ZSET scored by ``ready_at``; the pump only takes jobs with
``ready_at <= now`` (``peek_ready``). Producers use that score for:

- Jump the queue: earlier ``ready_at`` via ``at_front``.
- Peak-shave a burst: stagger readiness with ``spread``.

``ready_at`` is a lower bound, not a schedule: crossing it only makes the job
ready. When it actually runs still depends on the pump tick, the namespace
budget (``max_reserved`` + AIMD), a free concurrency slot, and Celery.

The pending wait TTL starts at ``max(enqueue time, ready_at)``, so deliberate
future readiness does not consume the job's queue-wait budget.

``ready_at`` on ``submit`` may be:
- ``None`` — use now (ready immediately),
- ``float`` — same absolute timestamp for every item,
- ``(index, item) -> float`` — per-item timestamp (``index`` is 0-based across
  the whole ``submit`` call, not within an admission chunk),
- a submit-bound schedule such as ``spread(window_seconds)``.

Only reorders pending: never preempts reserved work.
"""
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union


@dataclass(frozen=True)
class SpreadSpec:
    window_seconds: float
    base: float
    jitter_seconds: float = 0.0

    def resolve(self, index: int, count: int) -> float:
        step = float(self.window_seconds) / max(1, int(count))
        timestamp = self.base + index * step
        if self.jitter_seconds:
            timestamp += random.uniform(0.0, float(self.jitter_seconds))
        return timestamp


# Absolute timestamp, per-item callback, or a submit-bound schedule.
ReadyAtSpec = Optional[Union[float, Callable[[int, Any], float], SpreadSpec]]


def resolve_ready_at(
    spec: ReadyAtSpec,
    index: int,
    item: Any,
    *,
    count: Optional[int] = None,
) -> Optional[float]:
    """Resolve one item's ``ready_at``; ``None`` means "use now"."""
    if spec is None:
        return None
    if isinstance(spec, SpreadSpec):
        return spec.resolve(index, count or 1)
    if callable(spec):
        return float(spec(index, item))
    return float(spec)


def at_front(offset_seconds: float = 0.0, *, base: Optional[float] = None) -> float:
    """Return a timestamp slightly before ``base`` (default: now) to jump the queue.

    Prefer a small bounded ``offset_seconds`` over zero so other priority jobs
    are not always pushed behind.
    """
    base = time.time() if base is None else float(base)
    return base - max(0.0, float(offset_seconds))


def spread(
    window_seconds: float,
    *,
    base: Optional[float] = None,
    jitter_seconds: float = 0.0,
) -> SpreadSpec:
    """Evenly space submitted items over ``[base, base + window_seconds]``.

    Returns a schedule that ``submit`` binds to its normalized item count.
    Optional ``jitter_seconds`` adds ``[0, jitter]`` noise to avoid aligning
    items on the same pump tick.
    """
    return SpreadSpec(
        window_seconds=window_seconds,
        base=time.time() if base is None else float(base),
        jitter_seconds=jitter_seconds,
    )
