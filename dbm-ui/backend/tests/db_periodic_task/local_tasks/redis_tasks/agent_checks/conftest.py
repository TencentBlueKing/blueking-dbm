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
import importlib
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.db_periodic_task.dispatch.config import DEFAULT_MAX_REQUEUE_ATTEMPTS, DEFAULT_REQUEUE_COOLDOWN_SECONDS


@pytest.fixture(scope="module")
def base(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config")


@pytest.fixture(scope="module")
def redis_adapter(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter")


@pytest.fixture(scope="module")
def ai_tasks(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.dbm_aiagent.tasks")


@pytest.fixture
def make_config(base):
    def _make(**overrides):
        defaults = dict(
            lookback_days=14,
            ignore_cluster_domains=[],
            requeue_cooldown_seconds=DEFAULT_REQUEUE_COOLDOWN_SECONDS,
            max_requeue_attempts=DEFAULT_MAX_REQUEUE_ATTEMPTS,
            execution_timeout_seconds=540,
            enabled=True,
        )
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    return _make


@pytest.fixture
def make_cluster():
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
def fake_task_instance(redis_adapter, base, make_config):
    from backend.db_report.enums.redis_sub_type import RedisCheckSubType
    from backend.dbm_aiagent.agent.constants import DBMAgentCode

    def _make(**config_overrides):
        class _FakeTask(redis_adapter.RedisAgentCheckTask):
            config_cls = base.RedisAgentCheckConfig
            subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
            agent_code = DBMAgentCode.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK
            prompt_template = "cluster={cluster_domain}"
            task_key = "test.fake"

            def load_config(self):
                return base.RedisAgentCheckConfig(enabled=True, **config_overrides)

            def build_request(self, item, *, overrides=None):
                from backend.dbm_aiagent.tasks.invoker import AgentRequest

                domain = item.get("cluster_domain", f"cluster-{item['cluster_id']}.db")
                return AgentRequest(content=self.prompt_template.format(cluster_domain=domain))

        return _FakeTask()

    return _make
