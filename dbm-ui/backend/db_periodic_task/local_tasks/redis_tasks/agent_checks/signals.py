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
# This module is intentionally agent-check-specific. If a second domain
# (e.g. redis_backup) ever needs the same hard-timeout observability, do NOT
# extend this module — extract a generic helper into db_periodic_task/ and
# have both domains call it with their own outcome taxonomy.
import logging

from celery.signals import task_failure

from .base import OUTCOME_ERROR, OUTCOME_TIMEOUT_HARD

logger = logging.getLogger("root")


def agent_check_task_failure_handler(sender=None, task_id=None, exception=None, **_kwargs):
    """Log hard timeouts and unhandled errors for agent-check celery tasks.

    Connected per-task via ``register_agent_check_failure_handlers``, so this
    receiver only fires for the explicitly registered tasks. No name-based
    filtering is needed.

    The primary case is ``WorkerLostError``: Celery hits ``time_limit`` and
    SIGKILLs the worker before any in-task ``try/except`` can run, so this
    is the only place such failures can be observed in our logs.
    """
    # Lazy import: keeps module-load time low and avoids surprising failures
    # when billiard is unavailable in non-celery test environments.
    try:
        from billiard.exceptions import WorkerLostError
    except ImportError:
        WorkerLostError = None

    is_worker_lost = WorkerLostError is not None and isinstance(exception, WorkerLostError)
    outcome = OUTCOME_TIMEOUT_HARD if is_worker_lost else OUTCOME_ERROR
    task_name = getattr(sender, "name", "") or "<unknown>"
    logger.error(
        "%s: task_id=%s outcome=%s exc_type=%s: %s",
        task_name,
        task_id,
        outcome,
        type(exception).__name__ if exception else "None",
        exception,
    )


def register_agent_check_failure_handlers():
    """Connect the failure handler to each agent-check celery task explicitly.

    Invoked at module import time (see bottom of this file) so registration
    happens transparently when ``agent_checks`` is loaded — there is no
    separate hookup step the operator has to remember.

    Adding a new agent check requires appending its celery task to the
    tuple below; forgetting to do so is intentional friction (the new
    task simply will not have hard-timeout observability until registered).

    Idempotent: ``dispatch_uid`` ensures repeated imports / calls do not
    produce duplicate receivers, which matters for test environments where
    modules may be reloaded.
    """
    from .check_backend_data_skew import check_backend_data_skew_task
    from .check_backend_load_skew import check_backend_load_skew_task
    from .check_cluster_capacity_growth import check_cluster_capacity_growth_task

    agent_check_tasks = (
        check_cluster_capacity_growth_task,
        check_backend_data_skew_task,
        check_backend_load_skew_task,
    )
    for task in agent_check_tasks:
        task_failure.connect(
            agent_check_task_failure_handler,
            sender=task,
            dispatch_uid=f"agent_check_task_failure:{task.name}",
        )


# Auto-register on module import.
register_agent_check_failure_handlers()
