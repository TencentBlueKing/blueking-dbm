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
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.db_report.portrait.generator import RedisClusterPortraitGenerator
from backend.db_report.portrait.generator.base import (
    STATUS_AI_ERROR,
    STATUS_SUCCESS,
    PortraitInvalidParamException,
    PortraitRateLimitException,
)
from backend.db_report.portrait.mysql_dimensions import MysqlPortraitDimensionCode
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.dbm_aiagent.agent.constants import DBMAgentCode

pytestmark = pytest.mark.django_db

DOMAIN = "cache.portrait-redis.test.db"


class _RateLimitError(Exception):
    status_code = 429


@pytest.fixture(autouse=True)
def clean_reports():
    # ClusterPortraitReport writes are not rolled back by the django_db transaction.
    ClusterPortraitReport.objects.filter(cluster_domain=DOMAIN).delete()
    yield
    ClusterPortraitReport.objects.filter(cluster_domain=DOMAIN).delete()


@pytest.fixture
def cluster():
    return Cluster.objects.create(
        bk_biz_id=5005578,
        cluster_type=ClusterType.TendisPredixyTendisplusCluster.value,
        immute_domain=DOMAIN,
        name="portrait-redis",
    )


def _window():
    report_to = timezone.now() - timedelta(minutes=1)
    return report_to - timedelta(days=1), report_to


def _run(cluster, **kwargs):
    report_from, report_to = _window()
    return RedisClusterPortraitGenerator().run(cluster=cluster, report_from=report_from, report_to=report_to, **kwargs)


def test_agent_code_value():
    assert DBMAgentCode.REDIS_PORTRAIT_CLUSTER.value == "ai-rds-portrait"
    assert DBMAgentCode("ai-rds-portrait") == DBMAgentCode.REDIS_PORTRAIT_CLUSTER


def test_instantiation_binds_redis_attributes():
    generator = RedisClusterPortraitGenerator()
    assert generator.db_type == DBType.Redis
    assert generator.agent_code == DBMAgentCode.REDIS_PORTRAIT_CLUSTER
    assert generator.dimension_enum is RedisPortraitDimensionCode


def test_rejects_foreign_dimension(cluster):
    with patch.object(RedisClusterPortraitGenerator, "_call_agent") as call_agent:
        with pytest.raises(PortraitInvalidParamException):
            _run(cluster, dimensions=[MysqlPortraitDimensionCode.MYSQL_CHECKSUM_CHECK])
    call_agent.assert_not_called()
    assert not ClusterPortraitReport.objects.filter(cluster_domain=DOMAIN).exists()


def test_rejects_non_cluster():
    report_from, report_to = _window()
    with pytest.raises(PortraitInvalidParamException):
        RedisClusterPortraitGenerator().run(cluster=object(), report_from=report_from, report_to=report_to)


def test_success_persists_redis_report(cluster):
    raw = (
        "综述...\n"
        '[ai_result]{"ai_status": true, "report_url": "https://bk-dbm.example.com/ai-chat/share/abc/", '
        '"report_score": 87, "message": ""}[ai_result]'
    )
    with patch.object(RedisClusterPortraitGenerator, "_call_agent", return_value=raw) as call_agent:
        result = _run(cluster)

    assert DOMAIN in call_agent.call_args.args[0]
    assert result.status == STATUS_SUCCESS
    assert result.score == 87
    record = ClusterPortraitReport.objects.get(id=result.record_id)
    assert record.db_type == DBType.Redis.value
    assert record.score == 87
    assert record.share_url == "https://bk-dbm.example.com/ai-chat/share/abc/"


def test_rate_limit_rolls_back_placeholder(cluster):
    with patch.object(RedisClusterPortraitGenerator, "_call_agent", side_effect=_RateLimitError("too many")):
        with pytest.raises(PortraitRateLimitException):
            _run(cluster)
    assert not ClusterPortraitReport.objects.filter(cluster_domain=DOMAIN).exists()


def test_ai_rejected_persists_ai_error(cluster):
    raw = '[ai_result]{"ai_status": false, "report_url": "", "report_score": -1, "message": "缺少维度数据"}[ai_result]'
    with patch.object(RedisClusterPortraitGenerator, "_call_agent", return_value=raw):
        result = _run(cluster)

    assert result.status == STATUS_AI_ERROR
    assert result.error == "ai_rejected"
    record = ClusterPortraitReport.objects.get(id=result.record_id)
    assert record.summary == "[ai_rejected] 缺少维度数据"
    assert record.score == -1
