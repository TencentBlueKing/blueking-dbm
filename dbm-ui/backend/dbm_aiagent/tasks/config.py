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
from typing import ClassVar

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig, DispatchTaskConfig, IdempotenceMode

DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS = 540
AGENT_RESPONSE_LOG_MAX_CHARS = 2000

# Single source of truth for the AI queue / task / settings namespace.
AI_NAMESPACE = "ai"


@dataclass
class AITaskQueueConfig(DispatchQueueConfig):
    """Dispatch ceilings owned by the AI queue group."""

    namespace: ClassVar[str] = AI_NAMESPACE


@dataclass
class AITaskConfig(DispatchTaskConfig):
    """Runtime configuration for a registered task in the AI group.

    ``queue_namespace`` is intentionally not declared here: the dispatch registry
    stamps it from the bound queue (``queue_cls.namespace``) at registration, so
    the persisted config always targets the correct queue.

    ``execution_timeout_seconds`` is the single timeout knob: AgentHandler invoke
    and reserved-slot reclaim both follow it. The default is the agent invoke
    budget rather than the generic dispatch default.
    """

    execution_timeout_seconds: int = DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS


__all__ = (
    "AI_NAMESPACE",
    "AGENT_RESPONSE_LOG_MAX_CHARS",
    "AITaskQueueConfig",
    "AITaskConfig",
    "DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS",
    "DispatchTaskConfig",
    "IdempotenceMode",
    "DispatchQueueConfig",
)
