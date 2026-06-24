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
import pytest

from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models.redis_check_report import RedisCheckReport
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter

pytestmark = pytest.mark.django_db


def _report_kwargs(instance: str, state: str = ReportStateType.ABNORMAL.value) -> dict:
    return {
        "cluster_id": 18473001,
        "subtype": RedisCheckSubType.ConfigInconsistent.value,
        "cluster": "redis-conf-check.test.db",
        "cluster_type": "TendisPredixyRedisCluster",
        "bk_biz_id": 1001,
        "bk_cloud_id": 0,
        "report_day": 20260625,
        "creator": "pytest",
        "state": state,
        "msg": "test",
        "instance": instance,
    }


def test_failed_days_is_scoped_by_instance():
    RedisCheckReport.objects.filter(cluster_id=18473001, subtype=RedisCheckSubType.ConfigInconsistent.value).delete()

    first = RedisCheckReport.create_by_cluster_subtype(**_report_kwargs("1.1.1.1:30000"))
    second = RedisCheckReport.create_by_cluster_subtype(**_report_kwargs("1.1.1.2:30000"))

    assert first.failed_days == 1
    assert second.failed_days == 1


def test_failed_days_increments_for_same_instance():
    RedisCheckReport.objects.filter(cluster_id=18473001, subtype=RedisCheckSubType.ConfigInconsistent.value).delete()

    first = RedisCheckReport.create_by_cluster_subtype(**_report_kwargs("1.1.1.1:30000"))
    second = RedisCheckReport.create_by_cluster_subtype(**_report_kwargs("1.1.1.1:30000"))

    assert first.failed_days == 1
    assert second.failed_days == 2


def test_bulk_add_mode_preserves_instance_failed_days():
    RedisCheckReport.objects.filter(cluster_id=18473001, subtype=RedisCheckSubType.ConfigInconsistent.value).delete()

    writer = RedisReportWriter()
    rows = [_report_kwargs("1.1.1.1:30000"), _report_kwargs("1.1.1.2:30000")]
    writer.write_redis_reports(rows)

    failed_days = {
        row.instance: row.failed_days
        for row in RedisCheckReport.objects.filter(cluster_id=18473001).order_by("instance")
    }
    assert failed_days == {"1.1.1.1:30000": 1, "1.1.1.2:30000": 1}


def test_bulk_add_mode_increments_duplicate_instance_like_sequential_writes():
    RedisCheckReport.objects.filter(cluster_id=18473001, subtype=RedisCheckSubType.ConfigInconsistent.value).delete()

    writer = RedisReportWriter()
    writer.write_redis_reports([_report_kwargs("1.1.1.1:30000"), _report_kwargs("1.1.1.1:30000")])

    assert list(
        RedisCheckReport.objects.filter(cluster_id=18473001)
        .order_by("create_at")
        .values_list("failed_days", flat=True)
    ) == [1, 2]
