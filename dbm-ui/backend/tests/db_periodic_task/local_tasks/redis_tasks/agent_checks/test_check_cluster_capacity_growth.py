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
# Unit tests for the capacity-growth check's producer-side eviction filter.
#
# Covers:
#   * ``_batch_query_maxmemory_policies`` parsing / chunking
#   * ``filter_produce_candidates`` keep / skip / abort decisions
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
        bk_cloud_id=0,
        immute_domain="cache.test.db",
        major_version="Redis-6",
        cluster_type="TwemproxyRedisInstance",
    )


# ---------------------------------------------------------------------------
# _batch_query_maxmemory_policies
# ---------------------------------------------------------------------------
class TestBatchQueryMaxmemoryPolicies:
    _API = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks." "check_cluster_capacity_growth.DBConfigApi"

    def test_batches_by_type_and_version(self, cap_growth):
        c1 = SimpleNamespace(
            id=1,
            bk_biz_id=1,
            immute_domain="a.db",
            major_version="Redis-6",
            cluster_type="TwemproxyRedisInstance",
        )
        c2 = SimpleNamespace(
            id=2,
            bk_biz_id=1,
            immute_domain="b.db",
            major_version="Redis-6",
            cluster_type="TwemproxyRedisInstance",
        )
        c3 = SimpleNamespace(
            id=3,
            bk_biz_id=1,
            immute_domain="c.db",
            major_version="Redis-7",
            cluster_type="PredixyRedisCluster",
        )
        with patch(self._API) as api:
            api.batch_get_conf_item.side_effect = [
                {
                    "content": {
                        "a.db": {"maxmemory-policy": "noeviction"},
                        "b.db": {"maxmemory-policy": "AllKeys-LRU"},
                    }
                },
                {"content": {"c.db": {"maxmemory-policy": "volatile-lru"}}},
            ]
            policies = cap_growth._batch_query_maxmemory_policies([c1, c2, c3])

        assert policies == {"a.db": "noeviction", "b.db": "allkeys-lru", "c.db": "volatile-lru"}
        assert api.batch_get_conf_item.call_count == 2

    def test_chunks_same_group_at_max_batch_size(self, cap_growth):
        batch_size = cap_growth.MAXMEMORY_POLICY_BATCH_SIZE
        assert batch_size == 20
        clusters = [
            SimpleNamespace(
                id=i,
                bk_biz_id=1,
                immute_domain=f"c{i}.db",
                major_version="Redis-6",
                cluster_type="TwemproxyRedisInstance",
            )
            for i in range(batch_size + 5)
        ]

        def _batch_response(params):
            return {"content": {domain: {"maxmemory-policy": "noeviction"} for domain in params["level_values"]}}

        with patch(self._API) as api:
            api.batch_get_conf_item.side_effect = lambda params: _batch_response(params)
            policies = cap_growth._batch_query_maxmemory_policies(clusters)

        assert len(policies) == batch_size + 5
        assert api.batch_get_conf_item.call_count == 2
        sizes = [len(call.kwargs["params"]["level_values"]) for call in api.batch_get_conf_item.call_args_list]
        assert sizes == [batch_size, 5]

    def test_missing_domain_yields_empty_policy(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.batch_get_conf_item.return_value = {"content": {}}
            policies = cap_growth._batch_query_maxmemory_policies([fake_cluster])

        assert policies == {fake_cluster.immute_domain: ""}

    def test_batch_api_failure_raises(self, cap_growth, fake_cluster):
        with patch(self._API) as api:
            api.batch_get_conf_item.side_effect = RuntimeError("batch 500")
            with pytest.raises(RuntimeError, match="batch 500"):
                cap_growth._batch_query_maxmemory_policies([fake_cluster])


# ---------------------------------------------------------------------------
# filter_produce_candidates
# ---------------------------------------------------------------------------
class TestFilterProduceCandidates:
    @staticmethod
    def _patch_policies(cap_growth, mapping):
        return patch.object(cap_growth, "_batch_query_maxmemory_policies", return_value=mapping)

    def test_noeviction_keeps_item(self, cap_growth, fake_cluster):
        item = {"cluster_id": fake_cluster.id, "cluster": fake_cluster, "cluster_domain": fake_cluster.immute_domain}
        with self._patch_policies(cap_growth, {fake_cluster.immute_domain: "noeviction"}), patch.object(
            cap_growth, "_write_eviction_skip_report"
        ):
            assert cap_growth.filter_produce_candidates([item]) == [item]

    def test_unknown_policy_keeps_item(self, cap_growth, fake_cluster):
        item = {"cluster_id": fake_cluster.id, "cluster": fake_cluster, "cluster_domain": fake_cluster.immute_domain}
        with self._patch_policies(cap_growth, {fake_cluster.immute_domain: ""}), patch.object(
            cap_growth, "_write_eviction_skip_report"
        ):
            assert cap_growth.filter_produce_candidates([item]) == [item]

    @pytest.mark.parametrize(
        "policy",
        ["allkeys-lru", "allkeys-lfu", "volatile-lru", "volatile-lfu", "allkeys-random", "volatile-ttl"],
    )
    def test_eviction_policy_drops_and_reports(self, cap_growth, fake_cluster, policy):
        item = {"cluster_id": fake_cluster.id, "cluster": fake_cluster, "cluster_domain": fake_cluster.immute_domain}
        with self._patch_policies(cap_growth, {fake_cluster.immute_domain: policy}), patch.object(
            cap_growth, "_write_eviction_skip_report"
        ) as write_report:
            kept = cap_growth.filter_produce_candidates([item])
        assert kept == []
        write_report.assert_called_once()
        assert policy in write_report.call_args.args[2]
        assert "eviction" in write_report.call_args.args[2]

    def test_batch_query_failure_raises_so_producer_holds_cursor(self, cap_growth, fake_cluster):
        item = {"cluster_id": fake_cluster.id, "cluster": fake_cluster, "cluster_domain": fake_cluster.immute_domain}
        with patch.object(
            cap_growth, "_batch_query_maxmemory_policies", side_effect=RuntimeError("dbconfig 500")
        ), patch.object(cap_growth, "_write_eviction_skip_report") as write_report:
            with pytest.raises(RuntimeError, match="dbconfig 500"):
                cap_growth.filter_produce_candidates([item])
        write_report.assert_not_called()

    def test_missing_cluster_is_kept(self, cap_growth):
        item = {"cluster_id": 999, "cluster_domain": "missing.db"}
        qs = MagicMock()
        qs.filter.return_value = []
        with patch.object(cap_growth, "Cluster") as cluster_cls, patch.object(
            cap_growth, "_batch_query_maxmemory_policies", return_value={}
        ) as batch_query, patch.object(cap_growth, "_write_eviction_skip_report") as write_report:
            cluster_cls.objects = qs
            assert cap_growth.filter_produce_candidates([item]) == [item]
        batch_query.assert_called_once()
        write_report.assert_not_called()


# ---------------------------------------------------------------------------
# _write_eviction_skip_report
# ---------------------------------------------------------------------------
class TestWriteEvictionSkipReport:
    @pytest.mark.django_db
    def test_creates_normal_skip_report(self, cap_growth, fake_cluster):
        from backend.db_report.enums import ReportStateType
        from backend.db_report.enums.redis_sub_type import RedisCheckSubType
        from backend.db_report.models import RedisCheckReport

        reason = "maxmemory-policy=allkeys-lru enables eviction"
        subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
        existing_report_ids = set(
            RedisCheckReport.objects.filter(cluster_id=fake_cluster.id, subtype=subtype.value).values_list(
                "id", flat=True
            )
        )
        cap_growth._write_eviction_skip_report(fake_cluster, subtype, reason)

        current_report_ids = set(
            RedisCheckReport.objects.filter(cluster_id=fake_cluster.id, subtype=subtype.value).values_list(
                "id", flat=True
            )
        )
        report = RedisCheckReport.objects.get(
            cluster_id=fake_cluster.id,
            subtype=subtype.value,
            id__in=current_report_ids - existing_report_ids,
        )
        assert report.cluster == fake_cluster.immute_domain
        assert report.cluster_type == fake_cluster.cluster_type
        assert report.bk_biz_id == fake_cluster.bk_biz_id
        assert report.bk_cloud_id == fake_cluster.bk_cloud_id
        assert report.shard == "all"
        assert report.instance == "all"
        assert report.status is True
        assert report.state == ReportStateType.NORMAL.value
        from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import SKIP_REPORT_MSG_PREFIX

        assert report.msg == f"{SKIP_REPORT_MSG_PREFIX} {reason}"
