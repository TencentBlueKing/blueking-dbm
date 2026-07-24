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
# Unit tests for ``RedisClusterSelector`` (candidate selection / skip windows).
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize(
    "raw",
    [
        {"candidate_page_size": 0},
        {"max_candidate_scan": -1},
        {"produce_low_watermark": 20, "produce_target_pending": 10},
        {"produce_target_pending": 2001},
    ],
)
def test_agent_check_config_rejects_unsafe_producer_values(raw):
    from django.core.exceptions import ValidationError

    from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import RedisAgentCheckConfig

    with pytest.raises(ValidationError):
        RedisAgentCheckConfig.validate_raw(raw)


class TestRedisClusterSelector:
    _CLUSTER = "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter.Cluster"
    _CLUSTER_OPERATE_RECORD = (
        "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter.ClusterOperateRecord"
    )

    @pytest.mark.django_db
    def test_skip_reports_use_normal_window(self, redis_adapter, base):
        from datetime import timedelta

        from django.utils import timezone

        from backend.db_report.enums import ReportStateType
        from backend.db_report.enums.redis_sub_type import RedisCheckSubType
        from backend.db_report.models import RedisCheckReport

        config = base.RedisAgentCheckConfig(
            enabled=True,
            candidate_page_size=10,
            max_candidate_scan=10,
            normal_skip_days=30,
        )
        selector = redis_adapter.RedisClusterSelector(
            config,
            RedisCheckSubType.ClusterCapacityGrowthRisk,
            task_key="test.fake",
        )

        class _FakeClusterQuerySet:
            def __init__(self, candidate_ids):
                self.candidate_ids = list(candidate_ids)
                self.excluded_ids = set()
                self.gt = None

            def exclude(self, **kwargs):
                self.excluded_ids.update(kwargs.get("id__in", set()))
                return self

            def filter(self, **kwargs):
                if "id__gt" in kwargs:
                    self.gt = kwargs["id__gt"]
                return self

            def order_by(self, *_args):
                return self

            def values_list(self, *_args, **_kwargs):
                return [
                    cid
                    for cid in self.candidate_ids
                    if cid not in self.excluded_ids and (self.gt is None or cid > self.gt)
                ]

        def _create_report(cluster_id, msg, created_at, state=ReportStateType.NORMAL.value):
            report = RedisCheckReport.objects.create(
                cluster_id=cluster_id,
                subtype=selector.subtype.value,
                report_day=int(created_at.strftime("%Y%m%d")),
                cluster=f"cluster-{cluster_id}.db",
                cluster_type="TwemproxyRedisInstance",
                bk_biz_id=1001,
                bk_cloud_id=0,
                shard="all",
                instance="all",
                status=True,
                state=state,
                msg=msg,
                creator="",
                updater="",
            )
            RedisCheckReport.objects.filter(id=report.id).update(create_at=created_at, update_at=created_at)

        now = timezone.now()
        _create_report(
            1,
            f"{base.SKIP_REPORT_MSG_PREFIX} maxmemory-policy=allkeys-lru enables eviction",
            now,
        )
        _create_report(
            2,
            f"{base.SKIP_REPORT_MSG_PREFIX} maxmemory-policy=volatile-lru enables eviction",
            now - timedelta(hours=25),
        )
        _create_report(3, "agent reported no capacity growth risk", now - timedelta(hours=25))

        fake_cluster_qs = _FakeClusterQuerySet(candidate_ids=[1, 2, 3, 4])

        def _filter_side_effect(*_args, **kwargs):
            if "id__in" in kwargs:
                ids = kwargs["id__in"]
                domain_qs = MagicMock()
                domain_qs.values_list.return_value = [(cid, f"cluster-{cid}.db") for cid in ids]
                return domain_qs
            return fake_cluster_qs

        with (
            patch(self._CLUSTER) as cluster_cls,
            patch(self._CLUSTER_OPERATE_RECORD) as operate_record_cls,
        ):
            cluster_cls.objects.filter.side_effect = _filter_side_effect
            operate_record_cls.objects.filter.return_value.filter.return_value.values_list.return_value = []

            clusters, next_cursor = selector.select_rotation(cursor=0, limit=10)
            assert [t["cluster_id"] for t in clusters] == [4]
            # id space exhausted after cluster 4 -> cursor wraps for the next run
            assert next_cursor == 0

    @staticmethod
    def _selector(**overrides):
        from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import RedisAgentCheckConfig
        from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter import RedisClusterSelector

        values = {
            "priority_alarm_names": ["Redis Capacity"],
            "priority_alarm_request_name_filter": True,
            "candidate_page_size": 10,
            "max_candidate_scan": 0,
        }
        values.update(overrides)
        return RedisClusterSelector(
            RedisAgentCheckConfig(**values),
            SimpleNamespace(value="capacity"),
            task_key="test.selector",
        )

    def test_rotation_cursor_stops_at_last_examined_id(self):
        selector = self._selector(candidate_page_size=3)
        base_qs = MagicMock()
        base_qs.filter.return_value.order_by.return_value.values_list.return_value = [1, 2, 3]
        with patch.object(selector, "_base_cluster_qs", return_value=(base_qs, MagicMock())), patch.object(
            selector,
            "_busy_cluster_ids",
            return_value=set(),
        ), patch.object(
            selector,
            "_to_items",
            side_effect=lambda ids: [{"cluster_id": cid, "cluster_domain": f"{cid}.db"} for cid in ids],
        ):
            items, next_cursor = selector.select_rotation(cursor=0, limit=1)

        assert [item["cluster_id"] for item in items] == [1]
        assert next_cursor == 1

    def test_rotation_honors_explicit_scan_limit(self):
        selector = self._selector(candidate_page_size=10, max_candidate_scan=2)
        base_qs = MagicMock()
        base_qs.filter.return_value.order_by.return_value.values_list.return_value = [1, 2, 3, 4]
        with patch.object(selector, "_base_cluster_qs", return_value=(base_qs, MagicMock())), patch.object(
            selector,
            "_busy_cluster_ids",
            return_value={1, 2},
        ), patch.object(selector, "_to_items", return_value=[]):
            items, next_cursor = selector.select_rotation(cursor=0, limit=3)

        assert items == []
        assert next_cursor == 2

    def test_alarm_request_and_post_filter_use_strategy_name(self):
        selector = self._selector()
        query = selector._build_alarm_query_string({"Redis Capacity"})
        assert 'strategy_name: "Redis Capacity"' in query
        assert "alert_name" not in query

    def test_priority_alarm_pagination_stops_at_domain_limit(self):
        selector = self._selector()
        now = MagicMock()
        now.__sub__.return_value.timestamp.return_value = 1
        now.timestamp.return_value = 2
        response = {
            "alerts": [
                {
                    "strategy_name": "Redis Capacity",
                    "tags": {"cluster_domain": f"{index}.db"},
                    "is_shielded": False,
                }
                for index in range(3)
            ],
            "total": 100,
        }
        with patch(
            "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter.BKMonitorV3Api.search_alert",
            return_value=response,
        ) as search_alert:
            domains = selector._pull_priority_alarm_cluster_domains(now, limit=1)

        assert domains == ["0.db"]
        search_alert.assert_called_once()

    def test_priority_alarm_api_failure_propagates(self):
        selector = self._selector()
        now = MagicMock()
        now.__sub__.return_value.timestamp.return_value = 1
        now.timestamp.return_value = 2
        with patch(
            "backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter.BKMonitorV3Api.search_alert",
            side_effect=RuntimeError("monitor unavailable"),
        ), pytest.raises(RuntimeError, match="monitor unavailable"):
            selector._pull_priority_alarm_cluster_domains(now, limit=1)

    def test_to_items_drops_clusters_missing_during_materialization(self):
        selector = self._selector()
        domain_qs = MagicMock()
        domain_qs.values_list.return_value = [(1, "one.db")]
        with patch(self._CLUSTER) as cluster_cls:
            cluster_cls.objects.filter.return_value = domain_qs
            assert selector._to_items([1, 2]) == [{"cluster_id": 1, "cluster_domain": "one.db"}]
