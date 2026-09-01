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
import logging
from typing import Type

from backend.db_periodic_task.dispatch.registry import register_dispatch_task
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.base import AITask
from backend.dbm_aiagent.tasks.config import AITaskConfig

logger = logging.getLogger("root")


def ai_task(
    *,
    agent_code: DBMAgentCode,
    config_cls: type[AITaskConfig] = AITaskConfig,
    db_type: str = "",
):
    """Register an AITask consumer with the shared dispatch infra.

    Wraps ``register_dispatch_task``. Both ``task_key`` (from ``config_cls.task_key``)
    and ``namespace`` (from the bound ``queue_cls``) are derived, so you only declare
    the ``config_cls`` binding and let ``queue_cls`` choose the queue.

    Minimal shape:

        @ai_task(
            agent_code=DBMAgentCode.REDIS_BACKEND_DATA_SKEW_CHECK,
            config_cls=BackendDataSkewCheckConfig,
            db_type="redis",
        )
        class CheckBackendDataSkewTask(RedisAgentCheckTask):
            subtype = RedisCheckSubType.BackendDataSkew
            prompt_template = "cluster_domains: [{cluster_domain}]"

    The registered metadata copies ``cls.prompt_template``, which is the one the
    runtime actually formats.

    Periodic production is caller-owned: register your own
    ``@register_periodic_task`` that selects targets and calls
    ``task.submit(items)``.
    """

    def decorator(cls: Type[AITask]):
        if not issubclass(cls, AITask):
            raise TypeError("@ai_task can only decorate AITask subclasses")

        metadata = {
            "agent_code": str(agent_code),
            "db_type": db_type,
            "prompt_template": getattr(cls, "prompt_template", "") or "",
        }

        registered = register_dispatch_task(
            config_cls=config_cls,
            metadata=metadata,
        )(cls)

        cls.agent_code = agent_code
        return registered

    return decorator
