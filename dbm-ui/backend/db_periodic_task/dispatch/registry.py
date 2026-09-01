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
from typing import Optional, Type

from blueapps.core.celery.celery import app

from backend.db_periodic_task.dispatch.base import DispatchTask

logger = logging.getLogger("root")

DISPATCH_REGISTRY: dict[str, Type[DispatchTask]] = {}


@app.task(bind=True, name="backend.db_periodic_task.dispatch.registry.dispatch_execute_job")
def dispatch_execute_job(self, job_id: str):
    """Generic worker for all registered dispatch jobs."""
    DispatchTask.execute_job(job_id)


def register_dispatch_task(
    *,
    config_cls=None,
    metadata: Optional[dict] = None,
):
    """Register a DispatchTask consumer with the shared dispatch infra.

    Required class methods:
    - ``execute``: run one work item.

    Identity is derived from the bound classes — the single source of truth:

    - ``task_key`` comes from ``config_cls.task_key`` and must be a non-empty
      string before registration (pre-registered task identity).
    - ``namespace`` comes from the bound ``queue_cls`` (``queue_cls.namespace`` →
      ``queue_cls.config_cls.namespace``): the routing and rate-limit isolation
      boundary. The queue must bind a non-empty namespace.

    The persisted config's identity keys are stamped from these bindings so
    ``save_to_db`` always targets the correct queue/task row.

    ``config_cls`` is optional; when omitted the task uses the base
    ``DispatchTaskConfig`` (whose ``task_key`` is empty, so registration fails —
    bind a real config_cls).

    Import the module from startup-loaded code so the decorator runs.
    """

    def decorator(cls: Type[DispatchTask]):
        if not issubclass(cls, DispatchTask):
            raise TypeError("@register_dispatch_task can only decorate DispatchTask subclasses")

        if config_cls is not None:
            cls.config_cls = config_cls

        # namespace: owned by the bound queue (queue.config_cls.namespace).
        namespace = cls.queue_cls.namespace
        if not namespace:
            raise ValueError(
                f"{cls.__name__} must bind a queue with a non-empty namespace "
                f"(set queue_cls to a DispatchQueue whose config_cls.namespace is set)"
            )

        # task_key: owned by the bound config_cls; registration requires it non-empty.
        task_key = getattr(cls.config_cls, "task_key", "") or ""
        if not task_key:
            raise ValueError(f"{cls.__name__}.config_cls.task_key must be a non-empty string before registration")

        existing = DISPATCH_REGISTRY.get(task_key)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"task_key={task_key!r} already registered by "
                f"{existing.__module__}.{existing.__name__}; "
                f"cannot register {cls.__module__}.{cls.__name__}"
            )

        cls.namespace = namespace
        cls.task_key = task_key
        # Keep the persisted config identity aligned with the binding so that
        # save_to_db() targets the correct queue/task row; queue_namespace is
        # derived from the bound queue, not hand-written on the config.
        cls.config_cls.task_key = task_key
        cls.config_cls.queue_namespace = namespace

        DISPATCH_REGISTRY[task_key] = cls
        cls.queue_cls.register_task_metadata(
            task_key,
            {
                "task_key": task_key,
                "namespace": namespace,
                "class": f"{cls.__module__}.{cls.__name__}",
                **(metadata or {}),
            },
        )

        return cls

    return decorator


def register_failure_handlers():
    from celery.signals import task_failure

    from backend.db_periodic_task.dispatch.signals import dispatch_failure_handler

    task_failure.connect(
        dispatch_failure_handler,
        sender=dispatch_execute_job,
        dispatch_uid="dispatch_failure:dispatch_execute_job",
    )
