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
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.dispatch.portrait_queue import PortraitQueue
from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY
from backend.db_report.portrait.generator import RedisClusterPortraitGenerator

# ---------------------------------------------------------------- config


@pytest.fixture
def redis_cfg(portrait_config):
    return portrait_config.RedisPortraitReportConfig


def test_redis_config_defaults(redis_cfg):
    config = redis_cfg()
    assert redis_cfg.task_key == "redis.cluster_portrait"
    assert config.enabled is False
    assert config.daily_shuffle_limit == 100
    assert config.cluster_types == []
    assert config.resolve_cluster_types() == [ct.value for ct in ClusterType.redis_cluster_types()]


def test_mysql_config_default_cluster_types_unchanged(portrait_config):
    config = portrait_config.MysqlPortraitReportConfig()
    assert config.daily_shuffle_limit == 0
    assert config.resolve_cluster_types() == [
        ClusterType.TenDBSingle.value,
        ClusterType.TenDBHA.value,
        ClusterType.TenDBCluster.value,
    ]


def test_configured_cluster_types_override_default(redis_cfg):
    config = redis_cfg.from_raw({"cluster_types": [ClusterType.TendisTwemproxyRedisInstance.value]})
    assert config.resolve_cluster_types() == [ClusterType.TendisTwemproxyRedisInstance.value]


def test_validate_raw_accepts_valid_cluster_types(redis_cfg):
    redis_cfg.validate_raw(
        {"cluster_types": [ClusterType.TendisPredixyTendisplusCluster.value], "daily_shuffle_limit": 10}
    )
    redis_cfg.validate_raw({"cluster_types": []})


@pytest.mark.parametrize(
    "cluster_types",
    [
        "TwemproxyRedisInstance",
        [1],
        ["not_a_cluster_type"],
        [ClusterType.TenDBHA.value, "bogus"],
    ],
)
def test_validate_raw_rejects_invalid_cluster_types(redis_cfg, cluster_types):
    with pytest.raises(ValidationError):
        redis_cfg.validate_raw({"cluster_types": cluster_types})


def test_validate_raw_rejects_negative_daily_limit(redis_cfg):
    with pytest.raises(ValidationError):
        redis_cfg.validate_raw({"daily_shuffle_limit": -1})


# ---------------------------------------------------------------- consumer


def test_redis_task_registered_on_portrait_queue(portrait_pkg):
    assert DISPATCH_REGISTRY["redis.cluster_portrait"] is portrait_pkg.RedisPortraitReportTask
    assert portrait_pkg.RedisPortraitReportTask.queue_cls is PortraitQueue
    assert portrait_pkg.RedisPortraitReportTask.namespace == "cluster_portrait"
    assert DISPATCH_REGISTRY["mysql.cluster_portrait"] is portrait_pkg.MysqlPortraitReportTask


def test_redis_task_resolves_redis_generator(portrait_pkg):
    cluster = SimpleNamespace(cluster_type=ClusterType.TendisPredixyRedisCluster.value)
    generator = portrait_pkg.RedisPortraitReportTask().resolve_generator(cluster)
    assert isinstance(generator, RedisClusterPortraitGenerator)
