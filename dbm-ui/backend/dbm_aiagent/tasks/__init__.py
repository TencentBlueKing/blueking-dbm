# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

AI agent task adapter on top of ``backend.db_periodic_task.dispatch``.

Extension docs live in code comments/docstrings:
- ``dbm_aiagent.tasks.base.AITask`` for hooks and execution behavior.
- ``dbm_aiagent.tasks.registry.ai_task`` for registration examples.
"""

from backend.db_periodic_task.dispatch.registry import register_failure_handlers
from backend.dbm_aiagent.tasks.base import AITask
from backend.dbm_aiagent.tasks.config import (
    AI_NAMESPACE,
    DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS,
    AITaskConfig,
    AITaskQueueConfig,
)
from backend.dbm_aiagent.tasks.invoker import AgentInvoker, AgentRequest
from backend.dbm_aiagent.tasks.outcomes import AgentOutcome, DispatchOutcomeType
from backend.dbm_aiagent.tasks.queue import AITaskQueue
from backend.dbm_aiagent.tasks.registry import ai_task

register_failure_handlers()
