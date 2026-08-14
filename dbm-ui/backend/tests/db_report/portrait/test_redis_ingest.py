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
from unittest.mock import patch

import pytest

from backend.configuration.constants import DBType
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.enums import ReportStateType
from backend.db_report.portrait.exceptions import PortraitSDKBaseException
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.sdk import PortraitIngestSDK

pytestmark = pytest.mark.django_db


@pytest.fixture
def redis_ingest():
    from backend.db_report.portrait import redis_ingest as mod

    return mod


def _kwargs(redis_ingest, **overrides):
    params = dict(
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
        dimension=RedisPortraitDimensionCode.RELIABILITY,
        prefix="[全备]",
        messages=["缺备：3 个分片昨日无全备记录"],
    )
    params.update(overrides)
    return params


def test_prefix_join(redis_ingest):
    with patch.object(redis_ingest, "ingest_summary") as ingest:
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest, messages=["缺备 A", "缺备 B"]))
    assert ingest.call_args.kwargs["summary"] == "[全备] 缺备 A；缺备 B"
    assert ingest.call_args.kwargs["db_type"] == DBType.Redis
    assert ingest.call_args.kwargs["dimension"] == RedisPortraitDimensionCode.RELIABILITY


def test_truncates_summary_and_detail_url(redis_ingest):
    with patch.object(redis_ingest, "ingest_summary") as ingest:
        redis_ingest.ingest_redis_cluster_summary(
            **_kwargs(
                redis_ingest,
                messages=["x" * 5000],
                detail_url="u" * 2000,
            )
        )
    kwargs = ingest.call_args.kwargs
    assert len(kwargs["summary"]) == PortraitIngestSDK.MAX_SUMMARY_CHARS
    assert len(kwargs["detail_url"]) == PortraitIngestSDK.MAX_DETAIL_URL_CHARS


def test_sdk_exception_not_raised(redis_ingest):
    with patch.object(redis_ingest, "ingest_summary", side_effect=PortraitSDKBaseException("portrait boom")):
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest))


def test_bare_exception_not_raised(redis_ingest):
    with patch.object(redis_ingest, "ingest_summary", side_effect=RuntimeError("orm boom")):
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest))


def test_skips_empty_messages(redis_ingest):
    with patch.object(redis_ingest, "ingest_summary") as ingest:
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest, messages=[]))
    ingest.assert_not_called()


def test_always_writes_abnormal(redis_ingest):
    """只接 daily 源，不做节流：每次有异常都写，重复调用重复写。"""
    with patch.object(redis_ingest, "ingest_summary") as ingest:
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest))
        redis_ingest.ingest_redis_cluster_summary(**_kwargs(redis_ingest))
    assert ingest.call_count == 2


def test_ingest_abnormal_rows_groups_and_skips_normal(redis_ingest):
    cluster = SimpleNamespace(immute_domain="a.redis.db", bk_biz_id=1001)
    rows = [
        {"cluster": cluster, "state": ReportStateType.NORMAL, "msg": "ok", "subtype": "alone_instance"},
        {"cluster": cluster, "state": ReportStateType.ABNORMAL, "msg": "lonely master", "subtype": "alone_instance"},
        {"cluster": cluster, "state": ReportStateType.WARNING, "msg": "not running", "subtype": "status_abnormal"},
    ]
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_abnormal_cluster_rows(
            rows,
            dimension=RedisPortraitDimensionCode.TOPOLOGY_SCALE,
            prefix_by_subtype={"alone_instance": "[孤立实例]", "status_abnormal": "[实例状态]"},
        )
    assert ingest.call_count == 2
    prefixes = {call.kwargs["prefix"] for call in ingest.call_args_list}
    assert prefixes == {"[孤立实例]", "[实例状态]"}


def test_rollback_skips_skipped_and_backup_invalid(redis_ingest):
    report = SimpleNamespace(
        task_stage=TaskStage.SKIPPED.value,
        instance_ip="1.1.1.1",
        instance_port=30000,
        task_message="",
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
    )
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_rollback_exercise_portrait(report)
        report.task_stage = TaskStage.BACKUP_INVALID.value
        redis_ingest.ingest_rollback_exercise_portrait(report)
    ingest.assert_not_called()


def test_rollback_writes_terminal_success(redis_ingest):
    report = SimpleNamespace(
        task_stage=TaskStage.DONE.value,
        instance_ip="1.1.1.1",
        instance_port=30000,
        task_message="ok",
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
    )
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_rollback_exercise_portrait(report)
    ingest.assert_called_once()
    assert ingest.call_args.kwargs["prefix"] == "[回档演练]"
    assert "成功" in ingest.call_args.kwargs["messages"][0]


def test_rollback_prefers_ai_conclusion_over_truncated_logs(redis_ingest):
    from backend.db_services.redis.rollback.failure_analysis import AI_ANALYSIS_END_SENTINEL, AI_ANALYSIS_SENTINEL

    noisy = "Child pipeline failed\n" + ("ERR " * 200)
    report = SimpleNamespace(
        task_stage=TaskStage.ROLLBACK_FAILED.value,
        instance_ip="1.1.1.1",
        instance_port=30000,
        task_message=(
            f"{noisy}\n{AI_ANALYSIS_SENTINEL} 2026-08-13 13:00:00\n"
            "原因分类: 构造流程失败\n诊断: 子流程 boom\n建议: 查看 child-root-1\n"
            "AI耗时: 1.2s\n"
            f"{AI_ANALYSIS_END_SENTINEL}\n"
        ),
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
    )
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_rollback_exercise_portrait(report)
    extra = ingest.call_args.kwargs["messages"][0]
    assert "原因分类: 构造流程失败" in extra
    assert "诊断: 子流程 boom" in extra
    assert "建议: 查看 child-root-1" in extra
    assert "Child pipeline failed" not in extra
    assert "AI耗时" not in extra
    assert "ERR " not in extra


def test_rollback_falls_back_to_truncated_task_message(redis_ingest):
    report = SimpleNamespace(
        task_stage=TaskStage.ROLLBACK_FAILED.value,
        instance_ip="1.1.1.1",
        instance_port=30000,
        task_message="line1\n" + ("x" * 2000),
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
    )
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_rollback_exercise_portrait(report)
    extra = ingest.call_args.kwargs["messages"][0]
    raw_extra = extra.split("；", 1)[1]
    assert raw_extra.startswith("line1 ")
    assert len(raw_extra) == redis_ingest._ROLLBACK_FALLBACK_CHARS
    assert "x" * 2000 not in extra


def test_rollback_ai_analysis_failed_falls_back_to_logs(redis_ingest):
    from backend.db_services.redis.rollback.failure_analysis import AI_ANALYSIS_FAILED_SENTINEL

    report = SimpleNamespace(
        task_stage=TaskStage.ROLLBACK_FAILED.value,
        instance_ip="1.1.1.1",
        instance_port=30000,
        task_message=f"Child pipeline failed\n{AI_ANALYSIS_FAILED_SENTINEL} t\n诊断: 智能体调用失败",
        cluster_domain="a.redis.db",
        bk_biz_id=1001,
    )
    with patch.object(redis_ingest, "ingest_redis_cluster_summary") as ingest:
        redis_ingest.ingest_rollback_exercise_portrait(report)
    extra = ingest.call_args.kwargs["messages"][0]
    assert "Child pipeline failed" in extra
