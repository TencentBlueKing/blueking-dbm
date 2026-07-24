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

import math
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class DispatchJob:
    job_id: str
    task_key: str
    namespace: str
    work_item_id: str
    # Item identity handed to ``execute``; ``payload_json`` is the task-built
    # request body, and ``config_json`` is a frozen config snapshot (empty means
    # resolve the live config at execution time).
    work_item_data: dict = field(default_factory=dict)
    payload_json: str = ""
    config_json: str = ""
    retry_count: int = 0
    created_at: float = 0.0
    # Lower bound on when the pump may pick this job up, not a promised
    # execution time: the pending ZSET score.
    ready_at: float = 0.0
    # When the queue-wait budget runs out; cleared on reservation, since a
    # reserved job is bounded by the execution timeout instead.
    wait_deadline_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "DispatchJob":
        return cls(
            job_id=raw["job_id"],
            task_key=raw["task_key"],
            namespace=raw.get("namespace", ""),
            work_item_id=raw.get("work_item_id", ""),
            work_item_data=raw.get("work_item_data") or {},
            payload_json=raw.get("payload_json") or "",
            config_json=raw.get("config_json", ""),
            retry_count=int(raw.get("retry_count", 0)),
            created_at=float(raw.get("created_at", 0)),
            ready_at=float(raw.get("ready_at", 0)),
            wait_deadline_at=float(raw.get("wait_deadline_at", 0)),
        )


def build_job_id(task_key: str, work_item_id: str) -> str:
    return f"{task_key}:{work_item_id}"


def compute_wait_deadline(
    now: float,
    ready_at: float,
    wait_ttl: int,
    wait_deadline_at: float = 0.0,
) -> tuple[float, Optional[int]]:
    """Resolve the queue-wait deadline and its remaining TTL for one job.

    Shared by admission and requeue so the deadline bookkeeping stays in one
    place. ``wait_deadline_at`` 0 (unset) starts the budget at
    ``max(now, ready_at)`` — intentional future readiness (``spread``) does
    not consume the wait budget. Returns ``(deadline, ttl)``; ``ttl=None`` means
    the existing deadline has already expired and the caller must not accept it.
    """
    wait_ttl = max(1, int(wait_ttl))
    if not wait_deadline_at:
        deadline = max(now, float(ready_at)) + wait_ttl
        return deadline, math.ceil(deadline - now)
    ttl = min(wait_ttl, math.ceil(wait_deadline_at - now))
    if ttl < 1:
        return wait_deadline_at, None
    return wait_deadline_at, ttl


def resolve_task_key_from_job_id(job_id: str, registered: list[str]) -> str:
    """Longest-prefix match of ``job_id`` against registered task keys."""
    matched = ""
    for task_key in registered:
        prefix = f"{task_key}:"
        if job_id.startswith(prefix) and len(task_key) > len(matched):
            matched = task_key
    return matched


def work_item_id_from_job_id(job_id: str, task_key: str) -> str:
    """Strip the ``task_key:`` prefix off ``job_id`` to recover the work item id."""
    prefix = f"{task_key}:"
    if task_key and job_id.startswith(prefix):
        return job_id[len(prefix) :]
    return ""
