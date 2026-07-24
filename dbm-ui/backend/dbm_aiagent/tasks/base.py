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

from abc import abstractmethod
from typing import Any, Optional

from backend.db_periodic_task.dispatch.base import DispatchTask
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.config import AITaskConfig
from backend.dbm_aiagent.tasks.invoker import AgentInvoker, AgentRequest
from backend.dbm_aiagent.tasks.outcomes import AgentOutcome
from backend.dbm_aiagent.tasks.queue import AITaskQueue

__all__ = ["AITask"]


class AITask(DispatchTask):
    """AI adapter: builds agent requests and invokes AgentHandler.

    Extension guide:
    1. Subclass ``AITask`` and implement ``build_request``.
    2. Register with ``@ai_task(...)``.
    3. Submit work via ``submit(items)``; observe via ``pending_count`` / ``stats``.
    4. For periodic fan-out, write a caller-owned ``@register_periodic_task``
       that selects work items and calls ``task.submit(items)``.

    You normally do not implement ``execute`` or ``build_payload`` here:
    ``AITask`` uses ``AgentInvoker`` for execution, handles 429 requeue, and
    resolves agent timeouts.

    Optional hooks inherited from ``DispatchTask``:
    - ``on_before_execute`` for worker-side stale-state checks.
    - ``on_execute_complete`` for post-completion side effects; its ``outcome``
      is an ``AgentOutcome``, so ``outcome.response`` carries the agent reply.

    Item selection belongs in the producer before ``submit()``.
    AI jobs share ``AITaskQueue.namespace`` and that queue's per-tick / concurrency limits.
    """

    queue_cls = AITaskQueue
    agent_code: DBMAgentCode = None
    config_cls: type[AITaskConfig] = AITaskConfig

    @abstractmethod
    def build_request(self, item: Any, *, overrides: Optional[dict] = None) -> AgentRequest:
        """Build a content request for a single work item."""

    def on_execute_complete(
        self,
        item: Any,
        outcome: AgentOutcome,
        *,
        job: Optional[DispatchJob] = None,
    ) -> None:
        """Optional post-execute hook; ``outcome.response`` is the agent reply."""

    def _resolve_request(
        self,
        item: Any,
        *,
        overrides: Optional[dict] = None,
        job: Optional[DispatchJob] = None,
    ) -> AgentRequest:
        overrides = overrides or {}
        if job is not None and job.payload_json:
            request = AgentInvoker.deserialize_request(job.payload_json)
        else:
            request = self.build_request(item, overrides=overrides)
        if overrides.get("session_code"):
            request.session_code = overrides["session_code"]
        return request

    def build_payload(self, item: Any, *, overrides: Optional[dict] = None) -> str:
        """Freeze the agent request on the job so the worker skips rebuilding it."""
        return AgentInvoker.serialize_request(self._resolve_request(item, overrides=overrides or {}))

    def execute(
        self,
        item: Any,
        *,
        job: Optional[DispatchJob] = None,
        overrides: Optional[dict] = None,
    ) -> AgentOutcome:
        overrides = overrides or {}
        request = self._resolve_request(item, overrides=overrides, job=job)
        config = self._apply_submit_config_overrides(overrides)
        execution_timeout = overrides.get("execution_timeout_seconds", config.execution_timeout_seconds)

        return AgentInvoker.invoke(
            task_key=self.task_key,
            agent_code=self.agent_code,
            request=request,
            execution_timeout_seconds=execution_timeout,
            requeue_cooldown_seconds=config.requeue_cooldown_seconds,
            work_item_ref=self.work_item_id(item),
        )
