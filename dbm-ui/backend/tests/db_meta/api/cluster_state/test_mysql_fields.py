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
import random
from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone

from backend.db_meta.api.cluster_state import ClusterStateService
from backend.db_meta.api.cluster_state.fields import CapacityExtra
from backend.db_meta.api.cluster_state.registry import get_schema
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ClusterDBHAExt, ClusterState
from backend.db_monitor.tasks import sync_cluster_capacity_state
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.tests.db_meta.api.cluster_state.base import StateFieldTestCase, create_cluster

pytestmark = pytest.mark.django_db

MYSQL_HA_FIELDS = ["phase", "status", "running_ticket", "dbha_disabled", "capacity", "portrait_report"]


@pytest.fixture
def bk_biz_id():
    return random.randint(500000, 600000)


@pytest.fixture
def clusters(bk_biz_id):
    return [create_cluster(ClusterType.TenDBHA.value, bk_biz_id) for _ in range(3)]


def capacity(in_use: float):
    return round(in_use), CapacityExtra(used=in_use, total=100, in_use=in_use)


class TestMySQLSchemas:
    @pytest.mark.parametrize("cluster_type", [ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value])
    def test_fields(self, cluster_type):
        assert list(get_schema(cluster_type).get_fields()) == MYSQL_HA_FIELDS

    def test_tendbsingle_without_optional_fields(self):
        assert list(get_schema(ClusterType.TenDBSingle.value).get_fields()) == ["phase", "status", "running_ticket"]


class TestDBHADisabled(StateFieldTestCase):
    cluster_type = ClusterType.TenDBHA.value

    def test_mark_and_unmark(self, clusters):
        end_time = timezone.now() + timedelta(days=1)
        ClusterStateService.mark(clusters[0].id, "dbha_disabled", True, extra={"end_time": end_time.isoformat()})

        state = self.get_state(clusters[0], "dbha_disabled")
        assert state.value is True
        assert state.detail.end_time == end_time
        assert clusters[0].__class__.objects.get(id=clusters[0].id).is_dbha_disabled()
        # Native 字段写已有表，不写状态表
        assert not ClusterState.objects.filter(cluster_id=clusters[0].id).exists()
        assert self.get_state(clusters[1], "dbha_disabled").value is False

        ClusterStateService.unmark(clusters[0].id, "dbha_disabled")
        assert self.get_state(clusters[0], "dbha_disabled").value is False

    def test_mark_forever_and_false(self, clusters):
        ClusterStateService.mark(clusters[0].id, "dbha_disabled", "true")
        assert ClusterDBHAExt.objects.get(cluster_id=clusters[0].id).end_time.year == 9999
        ClusterStateService.mark(clusters[0].id, "dbha_disabled", False)
        assert not ClusterDBHAExt.objects.filter(cluster_id=clusters[0].id).exists()

    def test_expired_and_filter(self, clusters):
        ClusterStateService.mark(clusters[0].id, "dbha_disabled", True)
        ClusterDBHAExt.objects.create(cluster=clusters[1], end_time=timezone.now() - timedelta(minutes=1))
        assert self.get_state(clusters[1], "dbha_disabled").value is False

        ids = {cluster.id for cluster in clusters}
        assert self.filter_cluster_ids("state__dbha_disabled", "true", clusters) == {clusters[0].id}
        assert self.filter_cluster_ids("state__dbha_disabled", "false", clusters) == ids - {clusters[0].id}
        assert self.filter_cluster_ids("state__dbha_disabled", "true,false", clusters) == ids


class TestCapacity(StateFieldTestCase):
    cluster_type = ClusterType.TenDBHA.value

    def test_no_row_is_uncollected(self, clusters):
        state = self.get_state(clusters[0], "capacity")
        assert (state.value, state.display, state.detail) == (None, "", None)

    def test_bulk_mark_is_batched(self, clusters, django_assert_max_num_queries):
        values = {cluster.id: capacity(50 + index * 10.4) for index, cluster in enumerate(clusters)}
        # 查集群 1 次 + upsert 1 次，加上事务的 SAVEPOINT，与集群数无关
        with django_assert_max_num_queries(4):
            ClusterStateService.bulk_mark("capacity", values, operator="collector")

        states = self.get_states(clusters)
        assert [states[cluster.id]["capacity"].value for cluster in clusters] == [50, 60, 71]
        assert states[clusters[2].id]["capacity"].display == "71%"
        assert states[clusters[2].id]["capacity"].detail == CapacityExtra(used=70.8, total=100, in_use=70.8)

    def test_bulk_mark_update_keeps_creator(self, clusters):
        ClusterStateService.bulk_mark("capacity", {clusters[0].id: capacity(10)}, operator="first")
        first = ClusterState.objects.get(cluster_id=clusters[0].id, state_key="capacity")
        ClusterStateService.bulk_mark("capacity", {clusters[0].id: capacity(20)}, operator="second")

        record = ClusterState.objects.get(cluster_id=clusters[0].id, state_key="capacity")
        assert (record.id, record.state_int_value, record.creator, record.updater) == (first.id, 20, "first", "second")
        assert record.update_at >= first.update_at

    def test_range_filter(self, clusters):
        ClusterStateService.bulk_mark("capacity", {clusters[0].id: capacity(30), clusters[1].id: capacity(90)})
        # 没有采集到容量的集群不命中任何范围
        assert self.filter_cluster_ids("state__capacity__gte", "80", clusters) == {clusters[1].id}
        assert self.filter_cluster_ids("state__capacity__lte", "80", clusters) == {clusters[0].id}

    def test_bulk_unmark(self, clusters):
        ClusterStateService.bulk_mark("capacity", {cluster.id: capacity(10) for cluster in clusters})
        ClusterStateService.bulk_unmark("capacity", [clusters[0].id, clusters[1].id])
        records = ClusterState.objects.filter(
            cluster_id__in=[cluster.id for cluster in clusters], state_key="capacity"
        )
        assert set(records.values_list("cluster_id", flat=True)) == {clusters[2].id}


class TestSyncCapacityState(StateFieldTestCase):
    cluster_type = ClusterType.TenDBHA.value

    def test_sync_overwrites_scope(self, bk_biz_id, clusters):
        stats = {cluster.immute_domain: {"used": 40, "total": 100, "in_use": 40.0} for cluster in clusters}
        stats["not.managed.db"] = {"used": 1, "total": 2, "in_use": 50.0}
        sync_cluster_capacity_state(bk_biz_id, ClusterType.TenDBHA.value, stats)
        assert {state["capacity"].value for state in self.get_states(clusters).values()} == {40}

        # 下一轮没有采到 clusters[0]，清除旧值；没有 in_use 的视为无效
        stats.pop(clusters[0].immute_domain)
        stats[clusters[1].immute_domain] = {"used": 40}
        sync_cluster_capacity_state(bk_biz_id, ClusterType.TenDBHA.value, stats)
        states = self.get_states(clusters)
        assert [states[cluster.id]["capacity"].value for cluster in clusters] == [None, None, 40]

    def test_skip_cluster_type_without_capacity(self, bk_biz_id):
        cluster = create_cluster(ClusterType.TenDBSingle.value, bk_biz_id)
        sync_cluster_capacity_state(
            bk_biz_id, ClusterType.TenDBSingle.value, {cluster.immute_domain: {"used": 1, "total": 2, "in_use": 50.0}}
        )
        assert not ClusterState.objects.filter(cluster_id=cluster.id).exists()


class TestPortraitReport(TestCase, StateFieldTestCase):
    # 画像报告表在 report_db；pytest-django 3.9 的 django_db 标记不支持 databases，用 TestCase 声明
    databases = {"default", "report_db"}
    cluster_type = ClusterType.TenDBHA.value

    def setUp(self):
        bk_biz_id = random.randint(500000, 600000)
        self.clusters = [create_cluster(ClusterType.TenDBHA.value, bk_biz_id) for _ in range(3)]

    @staticmethod
    def create_report(cluster, share_url: str, report_to_time, score: int = 90):
        return ClusterPortraitReport.objects.create(
            bk_biz_id=cluster.bk_biz_id,
            db_type="mysql",
            cluster_domain=cluster.immute_domain,
            report_from_time=report_to_time,
            report_to_time=report_to_time,
            share_url=share_url,
            score=score,
            creator="admin",
        )

    def test_latest_report(self):
        clusters = self.clusters
        now = timezone.now()
        self.create_report(clusters[0], "http://report/1", now, score=60)
        latest = self.create_report(clusters[0], "http://report/2", now + timedelta(hours=1), score=80)
        # 生成中的报告没有链接，不算
        self.create_report(clusters[0], "", now + timedelta(hours=2))
        # 早于集群创建时间的报告属于复用该域名的旧集群
        self.create_report(clusters[1], "http://report/old", clusters[1].create_at - timedelta(days=1))

        states = self.get_states(clusters)
        state = states[clusters[0].id]["portrait_report"]
        assert (state.value, state.display, state.detail.report_id, state.detail.score) == (
            "http://report/2",
            "查看报告",
            latest.id,
            80,
        )
        assert states[clusters[1].id]["portrait_report"].value is None
        assert states[clusters[2].id]["portrait_report"].value is None

    def test_detail(self):
        clusters = self.clusters
        self.create_report(clusters[0], "http://report/1", timezone.now())
        detail = ClusterStateService.get_detail(clusters[0], "portrait_report").to_dict()
        assert detail["type"] == "kv"
        assert detail["data"]["url"] == "http://report/1"
        assert ClusterStateService.get_detail(clusters[1], "portrait_report") is None
