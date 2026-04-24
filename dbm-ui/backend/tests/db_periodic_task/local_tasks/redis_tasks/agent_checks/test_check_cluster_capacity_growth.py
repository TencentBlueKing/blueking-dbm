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
# Unit tests for the capacity-growth check's eviction-policy skip strategy.
#
# Covers:
#   * ``_query_maxmemory_policy`` parsing of dbconfig responses
#   * ``CheckClusterCapacityGrowthTask.extra_skip_check`` skip / proceed decisions
import importlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def cap_growth(django_db_setup, django_db_blocker):
    """Lazy import mirroring conftest's pattern for ``base``.

    Importing the module triggers periodic-task registration so we keep it
    behind ``django_db_blocker.unblock`` to avoid touching the real DB.
    """
    with django_db_blocker.unblock():
        return importlib.import_module(
            "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.check_cluster_capacity_growth"
        )


@pytest.fixture
def fake_cluster():
    return SimpleNamespace(
        id=42,
        bk_biz_id=1001,
        immute_domain="cache.test.db",
        major_version="Redis-6",
        cluster_type="TwemproxyRedisInstance",
    )


@pytest.fixture
def task(cap_growth):
    """Build the task without invoking ``__init__`` (which would touch SystemSettings)."""
    return cap_growth.CheckClusterCapacityGrowthTask.__new__(cap_growth.CheckClusterCapacityGrowthTask)


# ---------------------------------------------------------------------------
# _query_maxmemory_policy
# ---------------------------------------------------------------------------
class TestQueryMaxmemoryPolicy:
    _API = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks." "check_cluster_capacity_growth.DBConfigApi"

    def test_returns_lowercased_value(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.query_conf_item.return_value = {"content": {"maxmemory-policy": "AllKeys-LRU"}}
            assert cap_growth._query_maxmemory_policy(fake_cluster) == "allkeys-lru"

    def test_missing_key_returns_empty_string(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.query_conf_item.return_value = {"content": {"maxmemory": "0"}}
            assert cap_growth._query_maxmemory_policy(fake_cluster) == ""

    def test_none_payload_returns_empty_string(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.query_conf_item.return_value = None
            assert cap_growth._query_maxmemory_policy(fake_cluster) == ""

    def test_passes_cluster_metadata_to_api(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.query_conf_item.return_value = {"content": {"maxmemory-policy": "noeviction"}}
            cap_growth._query_maxmemory_policy(fake_cluster)
        params = api.query_conf_item.call_args.kwargs["params"]
        assert params["bk_biz_id"] == "1001"
        assert params["level_value"] == "cache.test.db"
        assert params["conf_file"] == "Redis-6"
        assert params["namespace"] == "TwemproxyRedisInstance"


# ---------------------------------------------------------------------------
# CheckClusterCapacityGrowthTask.extra_skip_check
# ---------------------------------------------------------------------------
class TestExtraSkipCheckOverride:
    @staticmethod
    def _patch_policy(cap_growth, value):
        return patch.object(cap_growth, "_query_maxmemory_policy", return_value=value)

    def test_overrides_base_no_op(self, cap_growth, task):
        # The override must actually replace the base no-op so the
        # dispatcher's ``_has_extra_skip_check`` short-circuit does the
        # right thing.
        from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks import base

        assert task._has_extra_skip_check() is True
        assert (
            cap_growth.CheckClusterCapacityGrowthTask.extra_skip_check
            is not base.BaseRedisAgentCheckTask.extra_skip_check
        )

    def test_noeviction_does_not_skip(self, cap_growth, task, fake_cluster):
        with self._patch_policy(cap_growth, "noeviction"):
            assert task.extra_skip_check(fake_cluster) == (False, "")

    def test_unknown_policy_does_not_skip(self, cap_growth, task, fake_cluster):
        # Empty result means dbconfig didn't return the key; default is noeviction
        # (see Redis dbconf migration), so we must not skip.
        with self._patch_policy(cap_growth, ""):
            assert task.extra_skip_check(fake_cluster) == (False, "")

    @pytest.mark.parametrize(
        "policy",
        ["allkeys-lru", "allkeys-lfu", "volatile-lru", "volatile-lfu", "allkeys-random", "volatile-ttl"],
    )
    def test_eviction_policy_skips(self, cap_growth, task, fake_cluster, policy):
        with self._patch_policy(cap_growth, policy):
            skipped, reason = task.extra_skip_check(fake_cluster)
        assert skipped is True
        assert policy in reason
        assert "eviction" in reason
