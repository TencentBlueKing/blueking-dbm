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
# Shared fixtures for agent_checks unit tests.
#
# ``base`` is imported lazily behind ``django_db_blocker.unblock`` (mirroring
# the pattern used by ``local_tasks/redis_tasks/conftest.py``) because
# importing the module triggers periodic-task registration and DB access.
import importlib
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def base(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base")


@pytest.fixture(scope="module")
def signals(base, django_db_blocker):
    # ``signals`` re-exports the failure handler and registers it with celery's
    # task_failure signal. Loading it transitively imports the concrete check_*
    # modules, so we keep the same lazy-under-django-db-blocker pattern used
    # for ``base`` to avoid touching the real DB at collection time.
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.signals")


@pytest.fixture
def make_config(base):
    """Factory for a lightweight stand-in of ``BaseCheckConfig``.

    Real ``BaseCheckConfig`` works fine for most tests, but a ``SimpleNamespace``
    is friendlier when a test wants to override a single field without
    listing every default.
    """

    def _make(**overrides):
        defaults = dict(
            lookback_days=14,
            ignore_cluster_domains=[],
            rate_limit_cooldown_seconds=60,
            max_rate_limit_retries=3,
            agent_invoke_timeout_seconds=base.DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS,
            agent_soft_time_limit_seconds=base.DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS,
            agent_hard_time_limit_seconds=base.DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS,
        )
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    return _make


@pytest.fixture
def make_cluster():
    """Factory for a fake Cluster row suitable for ``_should_skip`` / ``execute_agent_check``."""

    def _make(
        *,
        cluster_id: int = 1,
        domain: str = "r.test.db",
        phase: str = "online",
        age_days: int = 30,
    ):
        from django.utils import timezone

        return SimpleNamespace(
            id=cluster_id,
            immute_domain=domain,
            phase=phase,
            create_at=timezone.now() - timedelta(days=age_days),
        )

    return _make


@pytest.fixture
def celery_task_mock():
    """Mock bound Celery task: carries ``name``/``request.retries`` and a fake ``retry()``."""
    task = MagicMock()
    task.name = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.fake_task"
    task.request.retries = 0

    class _Retry(Exception):
        pass

    task.retry.side_effect = _Retry("retry scheduled")
    task._retry_exc = _Retry
    return task


@dataclass
class _ClusterIds:
    ids: list


@pytest.fixture
def fake_task_instance(base, make_config):
    """Build a minimal ``BaseRedisAgentCheckTask`` subclass instance for ``start()`` tests."""
    from backend.db_report.enums.redis_sub_type import RedisCheckSubType
    from backend.dbm_aiagent.agent.constants import DBMAgentCode

    def _make(**config_overrides):
        class _FakeTask(base.BaseRedisAgentCheckTask):
            subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
            agent_code = DBMAgentCode.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK
            prompt_template = "cluster={cluster_domain}"

            def load_config(self):
                return base.BaseCheckConfig(enabled=True, **config_overrides)

            def get_celery_task(self):
                return MagicMock(name="fake_celery_task")

        return _FakeTask()

    return _make
