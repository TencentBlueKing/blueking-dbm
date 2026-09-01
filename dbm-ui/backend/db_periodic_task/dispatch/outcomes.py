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
from dataclasses import dataclass
from typing import Optional

from backend.db_periodic_task.dispatch.config import DEFAULT_REQUEUE_COOLDOWN_SECONDS
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class DispatchOutcomeType(StrStructuredEnum):
    """Structured outcome tags for log aggregation and observability counters."""

    SUCCESS = EnumField("success", "Work item completed successfully")
    TIMEOUT = EnumField("timeout", "Execution exceeded its timeout")
    REQUEUED = EnumField("requeued", "Returned to pending after a non-terminal execute")
    REQUEUE_EXHAUSTED = EnumField("requeue_exhausted", "Requeue requested but denied or budget spent")
    ERROR = EnumField("error", "Unhandled execution error")
    SKIPPED = EnumField("skipped", "Skipped before execute")
    ENQUEUED = EnumField("enqueued", "Producer enqueued work item")
    ENQUEUE_DUPLICATE = EnumField("enqueue_duplicate", "Producer skipped enqueue due to dedupe")
    ENQUEUE_CAPACITY_REJECTED = EnumField("enqueue_capacity_rejected", "Queue admitted capacity exhausted")
    ENQUEUE_PRODUCER_PAUSED = EnumField(
        "enqueue_producer_paused",
        "Producer gate closed; submission rejected without enqueue",
    )
    ENQUEUE_DEADLINE_EXPIRED = EnumField(
        "enqueue_deadline_expired",
        "Wait deadline expired before the job could be enqueued; never retried",
    )
    ENQUEUE_UNAVAILABLE = EnumField("enqueue_unavailable", "Enqueue unavailable because Redis capacity is unproven")
    EXPIRED = EnumField("expired", "Orphaned or stale job discarded")


@dataclass
class DispatchOutcome:
    """Outcome of one work item, both as an ``execute`` result and as a
    ``submit`` enqueue receipt (the ``ENQUEUE_*`` outcome types)."""

    outcome: DispatchOutcomeType
    error: Optional[Exception] = None
    elapsed_seconds: float = -1.0
    should_requeue: bool = False
    requeue_cooldown_seconds: int = DEFAULT_REQUEUE_COOLDOWN_SECONDS
    # Outcome to report when a requeue request is denied: attempt budget spent,
    # wait deadline gone, or the job was already reaped. Falls back to ``outcome``.
    exhausted_outcome: Optional[DispatchOutcomeType] = None
