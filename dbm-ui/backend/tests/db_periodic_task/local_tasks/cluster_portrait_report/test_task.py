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
from datetime import date
from unittest.mock import patch

import pytest

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.scheduling import resolve_ready_at

pytestmark = pytest.mark.django_db

SCHEDULE_DATE = date(2026, 11, 10)
NOW = 1_800_000_000.0


def _cluster(domain, cluster_type, phase=ClusterPhase.ONLINE.value):
    return Cluster.objects.create(
        bk_biz_id=5005578,
        cluster_type=cluster_type,
        immute_domain=domain,
        name=domain.split(".")[0],
        phase=phase,
    )


def _mysql_clusters(count):
    return [_cluster(f"m{i}.portrait.test.db", ClusterType.TenDBHA.value) for i in range(count)]


def _redis_clusters(count):
    return [_cluster(f"r{i}.portrait.test.db", ClusterType.TendisPredixyTendisplusCluster.value) for i in range(count)]


def _select(task_module, cfg):
    clusters = task_module._select_daily_clusters(
        schedule_date=SCHEDULE_DATE,
        cluster_types=cfg.resolve_cluster_types(),
        ignore_cluster_domains=cfg.ignore_cluster_domains,
        daily_shuffle_limit=cfg.daily_shuffle_limit,
    )
    return {cluster.immute_domain for cluster in clusters}


class _Recorder:
    """记录每次 submit 的 (task_key, item, ready_at)，按调用顺序累积。"""

    def __init__(self):
        self.calls = []

    def patch(self, task):
        def submit(items, *, ready_at=None, **_overrides):
            for idx, item in enumerate(items):
                ready = resolve_ready_at(ready_at, idx, item, count=len(items))
                self.calls.append((task.task_key, item["cluster_domain"], ready))
            return [DispatchOutcome(outcome=DispatchOutcomeType.ENQUEUED) for _ in items]

        task.submit = submit
        return task

    def queue_order(self):
        return [domain for _key, domain, _ready in sorted(self.calls, key=lambda call: call[2])]


@pytest.fixture
def produce(portrait_task_module, portrait_pkg, portrait_config):
    def run(mysql_raw=None, redis_raw=None, failing_factories=()):
        recorder = _Recorder()
        # _portrait_task_classes() 返回可调用对象；这里用工厂注入预置配置的 Task 实例
        factories = list(failing_factories)
        if mysql_raw is not None:
            cfg = portrait_config.MysqlPortraitReportConfig.from_raw(mysql_raw)
            task = recorder.patch(portrait_pkg.MysqlPortraitReportTask(config=cfg))
            factories.append(lambda task=task: task)
        if redis_raw is not None:
            cfg = portrait_config.RedisPortraitReportConfig.from_raw(redis_raw)
            task = recorder.patch(portrait_pkg.RedisPortraitReportTask(config=cfg))
            factories.append(lambda task=task: task)

        with patch.object(portrait_task_module.env, "ENABLE_DBM_AI", True), patch.object(
            portrait_task_module, "_portrait_task_classes", return_value=factories
        ), patch.object(portrait_task_module.timezone, "localdate", return_value=SCHEDULE_DATE), patch.object(
            portrait_task_module.time, "time", return_value=NOW
        ):
            portrait_task_module.generate_cluster_portrait_report()
        return recorder

    return run


# ---------------------------------------------------------------- cluster selection


def test_default_cluster_types_split_by_engine_and_online_only(portrait_task_module, portrait_config):
    _cluster("ha.portrait.test.db", ClusterType.TenDBHA.value)
    _cluster("spider.portrait.test.db", ClusterType.TenDBCluster.value)
    _cluster("offline.portrait.test.db", ClusterType.TenDBHA.value, phase=ClusterPhase.OFFLINE.value)
    _cluster("predixy.portrait.test.db", ClusterType.TendisPredixyTendisplusCluster.value)
    _cluster("twem.portrait.test.db", ClusterType.TendisTwemproxyRedisInstance.value)
    _cluster("mongo.portrait.test.db", ClusterType.MongoReplicaSet.value)

    assert _select(portrait_task_module, portrait_config.MysqlPortraitReportConfig()) == {
        "ha.portrait.test.db",
        "spider.portrait.test.db",
    }
    redis_cfg = portrait_config.RedisPortraitReportConfig(daily_shuffle_limit=0)
    assert _select(portrait_task_module, redis_cfg) == {"predixy.portrait.test.db", "twem.portrait.test.db"}


def test_custom_cluster_types_and_ignore_domains(portrait_task_module, portrait_config):
    _cluster("predixy.portrait.test.db", ClusterType.TendisPredixyTendisplusCluster.value)
    _cluster("twem1.portrait.test.db", ClusterType.TendisTwemproxyRedisInstance.value)
    _cluster("twem2.portrait.test.db", ClusterType.TendisTwemproxyRedisInstance.value)

    cfg = portrait_config.RedisPortraitReportConfig.from_raw(
        {
            "cluster_types": [ClusterType.TendisTwemproxyRedisInstance.value],
            "ignore_cluster_domains": ["twem2.portrait.test.db"],
        }
    )
    assert _select(portrait_task_module, cfg) == {"twem1.portrait.test.db"}


def test_daily_shuffle_limit_rotates_buckets(portrait_task_module):
    clusters = _redis_clusters(5)
    cluster_types = [ClusterType.TendisPredixyTendisplusCluster.value]
    bucket_count = 3  # ceil(5 / 2)

    seen = set()
    for offset in range(bucket_count):
        day = date.fromordinal(SCHEDULE_DATE.toordinal() + offset)
        picked = portrait_task_module._select_daily_clusters(
            schedule_date=day, cluster_types=cluster_types, ignore_cluster_domains=[], daily_shuffle_limit=2
        )
        assert picked
        assert all((c.id + day.toordinal()) % bucket_count == 0 for c in picked)
        assert seen.isdisjoint(c.id for c in picked)
        seen.update(c.id for c in picked)
    assert seen == {c.id for c in clusters}


# ---------------------------------------------------------------- producer


def test_portrait_tasks_discovered_from_registry_in_registration_order(portrait_task_module, portrait_pkg):
    assert portrait_task_module._portrait_task_classes() == [
        portrait_pkg.MysqlPortraitReportTask,
        portrait_pkg.RedisPortraitReportTask,
    ]


def test_task_failing_to_load_config_does_not_block_others(produce):
    _redis_clusters(2)

    def broken_task():
        raise RuntimeError("config cache unavailable")

    recorder = produce(redis_raw={"enabled": True}, failing_factories=[broken_task])

    assert [key for key, _domain, _ready in recorder.calls] == ["redis.cluster_portrait"] * 2


def test_task_failing_to_select_clusters_does_not_block_others(produce, portrait_task_module):
    _mysql_clusters(1)
    _redis_clusters(2)
    real_build_items = portrait_task_module._build_items

    def build_items(task, schedule_date):
        if task.task_key == "mysql.cluster_portrait":
            raise RuntimeError("db blip")
        return real_build_items(task, schedule_date)

    with patch.object(portrait_task_module, "_build_items", side_effect=build_items):
        recorder = produce(mysql_raw={"enabled": True}, redis_raw={"enabled": True})

    assert {key for key, _domain, _ready in recorder.calls} == {"redis.cluster_portrait"}
    assert len(recorder.calls) == 2


def test_only_enabled_task_is_submitted(produce):
    _mysql_clusters(2)
    _redis_clusters(2)

    recorder = produce(mysql_raw={"enabled": False}, redis_raw={"enabled": True})

    assert {key for key, _domain, _ready in recorder.calls} == {"redis.cluster_portrait"}
    assert len(recorder.calls) == 2


def test_all_tasks_disabled_submits_nothing(produce):
    _mysql_clusters(1)
    recorder = produce(mysql_raw={"enabled": False}, redis_raw={"enabled": False})
    assert recorder.calls == []


def test_round_robin_interleave_with_zero_window(produce):
    _mysql_clusters(3)
    _redis_clusters(4)

    recorder = produce(mysql_raw={"enabled": True}, redis_raw={"enabled": True, "daily_shuffle_limit": 0})

    assert recorder.queue_order() == [
        "m0.portrait.test.db",
        "r0.portrait.test.db",
        "m1.portrait.test.db",
        "r1.portrait.test.db",
        "m2.portrait.test.db",
        "r2.portrait.test.db",
        "r3.portrait.test.db",
    ]
    ready_times = sorted(ready for _key, _domain, ready in recorder.calls)
    assert all(earlier < later for earlier, later in zip(ready_times, ready_times[1:]))
    assert max(ready_times) <= NOW


def test_round_robin_interleave_spreads_over_window(produce):
    _mysql_clusters(2)
    _redis_clusters(2)

    recorder = produce(
        mysql_raw={"enabled": True, "dispatch_spread_window_seconds": 40},
        redis_raw={"enabled": True, "dispatch_spread_window_seconds": 0, "daily_shuffle_limit": 0},
    )

    ready_by_domain = {domain: ready for _key, domain, ready in recorder.calls}
    assert ready_by_domain == {
        "m0.portrait.test.db": NOW,
        "r0.portrait.test.db": NOW + 10,
        "m1.portrait.test.db": NOW + 20,
        "r1.portrait.test.db": NOW + 30,
    }
