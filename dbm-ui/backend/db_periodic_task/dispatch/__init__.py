# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Producer-consumer dispatch infrastructure for periodic fan-out tasks.

Extension docs live in code comments/docstrings:
- ``dispatch.base.DispatchTask`` for generic consumer tasks.
- ``dispatch.registry.register_dispatch_task`` for registration.
- ``dbm_aiagent.tasks.base.AITask`` and ``dbm_aiagent.tasks.registry.ai_task``
  for AI adapter tasks.
"""

from backend.db_periodic_task.dispatch.admission import EnqueueStatus
from backend.db_periodic_task.dispatch.base import DispatchTask
from backend.db_periodic_task.dispatch.config import (
    DispatchPumpConfig,
    DispatchQueueConfig,
    DispatchTaskConfig,
    IdempotenceMode,
)
from backend.db_periodic_task.dispatch.job import DispatchJob, build_job_id
from backend.db_periodic_task.dispatch.observability import (
    DispatchStats,
    DispatchStatsSnapshot,
    QueueDispatchReport,
    TaskDispatchReport,
)
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.queue import DispatchQueue, DispatchQueueError
from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY, register_dispatch_task
from backend.db_periodic_task.dispatch.scheduling import at_front, spread

__all__ = [
    "DISPATCH_REGISTRY",
    "DispatchPumpConfig",
    "DispatchTaskConfig",
    "DispatchJob",
    "DispatchOutcome",
    "DispatchOutcomeType",
    "DispatchQueue",
    "DispatchQueueError",
    "DispatchStats",
    "DispatchStatsSnapshot",
    "DispatchTask",
    "EnqueueStatus",
    "IdempotenceMode",
    "DispatchQueueConfig",
    "QueueDispatchReport",
    "TaskDispatchReport",
    "at_front",
    "build_job_id",
    "register_dispatch_task",
    "spread",
]
