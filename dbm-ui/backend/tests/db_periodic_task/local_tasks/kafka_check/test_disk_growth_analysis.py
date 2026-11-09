# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

ITEM = {
    "cluster_id": 7,
    "domain": "kafka.test.db",
    "bk_biz_id": 3,
    "check_day": "2026-11-04",
    "run_kind": "morning",
    "retention_hours": 4,
    "report_ids": [11, 12],
    "hits": [
        {
            "ip": "127.0.0.1",
            "mount_point": "/data",
            "rule": "continuous_new_high",
            "peak": 62.0,
            "excess": 4.0,
            "daily_growth": 4.0,
            "peaks": [{"day": "2026-11-03", "peak": 58.0}, {"day": "2026-11-04", "peak": 62.0}],
        }
    ],
}


@pytest.fixture
def task(ana_mod):
    # 显式传入配置，避免实例化时去读 DB / 缓存
    return ana_mod.KafkaDiskGrowthAnalysisTask(config=ana_mod.KafkaDiskGrowthAnalysisConfig(enabled=True))


@pytest.fixture
def report_cls(ana_mod):
    with patch.object(ana_mod, "KafkaDiskGrowthReport") as report_cls:
        yield report_cls


def updated_with(report_cls):
    return report_cls.objects.filter.return_value.update.call_args[1]


class TestPrompt:
    def test_contains_judgement_data_and_skill_name(self, ana_mod):
        prompt = ana_mod.build_prompt(ITEM)
        assert "kafka-alarm-analyzer" in prompt
        assert "kafka.test.db" in prompt and "2026-11-04" in prompt
        assert "127.0.0.1 /data" in prompt and "当天峰值=62.0%" in prompt
        assert "58.0 → 62.0" in prompt
        assert "持续创新高" in prompt
        assert "集群级保留期: 4 小时" in prompt

    def test_unknown_retention(self, ana_mod):
        assert "集群级保留期: 未知" in ana_mod.build_prompt({**ITEM, "retention_hours": None})

    def test_all_hits_listed(self, ana_mod):
        second = {**ITEM["hits"][0], "ip": "127.0.0.2", "rule": "single_day_jump"}
        prompt = ana_mod.build_prompt({**ITEM, "hits": [ITEM["hits"][0], second]})
        assert "127.0.0.1 /data" in prompt and "127.0.0.2 /data" in prompt and "单日跳涨" in prompt

    def test_build_request_uses_prompt(self, ana_mod, task):
        assert task.build_request(ITEM).content == ana_mod.build_prompt(ITEM)


class TestTaskIdentity:
    def test_work_item_id_is_per_cluster_day_and_run(self, task):
        assert task.work_item_id(ITEM) == "kafka_disk_growth:7:2026-11-04:morning"
        assert task.work_item_id({**ITEM, "run_kind": "afternoon"}) != task.work_item_id(ITEM)

    def test_registered_with_kafka_inspect_agent(self, ana_mod):
        from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY
        from backend.dbm_aiagent.agent.constants import DBMAgentCode

        assert DISPATCH_REGISTRY["kafka.disk_growth_analysis"] is ana_mod.KafkaDiskGrowthAnalysisTask
        assert ana_mod.KafkaDiskGrowthAnalysisTask.agent_code == DBMAgentCode.KAFKA_INSPECT


class TestConfig:
    def test_default_and_disabled_by_default(self, ana_mod):
        config = ana_mod.KafkaDiskGrowthAnalysisConfig()
        assert config.max_submit_per_run == 50 and config.enabled is False

    def test_validate_ok(self, ana_mod):
        ana_mod.KafkaDiskGrowthAnalysisConfig.validate_raw({"enabled": True, "max_submit_per_run": 10})

    def test_validate_rejects_non_positive_limit(self, ana_mod):
        with pytest.raises(ValidationError):
            ana_mod.KafkaDiskGrowthAnalysisConfig.validate_raw({"max_submit_per_run": 0})

    def test_validate_rejects_unknown_field(self, ana_mod):
        with pytest.raises(ValidationError):
            ana_mod.KafkaDiskGrowthAnalysisConfig.validate_raw({"no_such_field": 1})


class TestOnBeforeExecute:
    def test_online_cluster_runs(self, ana_mod, task, report_cls):
        with patch.object(ana_mod.Cluster, "objects") as clusters:
            clusters.filter.return_value.first.return_value = SimpleNamespace(phase="online")
            assert task.on_before_execute(ITEM) is None
        report_cls.objects.filter.assert_not_called()

    def test_missing_cluster_skipped_and_reports_updated(self, ana_mod, task, report_cls):
        with patch.object(ana_mod.Cluster, "objects") as clusters:
            clusters.filter.return_value.first.return_value = None
            assert task.on_before_execute(ITEM) == "cluster not found"
        assert report_cls.objects.filter.call_args[1] == {"id__in": [11, 12]}
        assert updated_with(report_cls)["ai_status"] == "skipped"

    def test_offline_cluster_skipped(self, ana_mod, task, report_cls):
        with patch.object(ana_mod.Cluster, "objects") as clusters:
            clusters.filter.return_value.first.return_value = SimpleNamespace(phase="offline")
            assert "not online" in task.on_before_execute(ITEM)
        assert updated_with(report_cls)["ai_status"] == "skipped"


class TestOnExecuteComplete:
    @staticmethod
    def outcome(ana_mod, kind, response=None):
        return SimpleNamespace(outcome=getattr(ana_mod.DispatchOutcomeType, kind), response=response)

    def test_success(self, ana_mod, task, report_cls):
        task.on_execute_complete(ITEM, self.outcome(ana_mod, "SUCCESS", "  原因分类: 流量驱动  "))
        assert report_cls.objects.filter.call_args[1] == {"id__in": [11, 12]}
        kwargs = updated_with(report_cls)
        assert kwargs["ai_status"] == "success" and kwargs["ai_analysis"] == "原因分类: 流量驱动"

    def test_long_response_truncated(self, ana_mod, task, report_cls):
        task.on_execute_complete(ITEM, self.outcome(ana_mod, "SUCCESS", "x" * 5000))
        assert len(updated_with(report_cls)["ai_analysis"]) == ana_mod.AI_ANALYSIS_MAX_CHARS

    @pytest.mark.parametrize("response", [None, "", "   "])
    def test_empty_response_is_failed(self, ana_mod, task, report_cls, response):
        task.on_execute_complete(ITEM, self.outcome(ana_mod, "SUCCESS", response))
        assert updated_with(report_cls)["ai_status"] == "failed"

    @pytest.mark.parametrize("kind", ["TIMEOUT", "ERROR", "REQUEUE_EXHAUSTED"])
    def test_other_outcomes_are_failed(self, ana_mod, task, report_cls, kind):
        task.on_execute_complete(ITEM, self.outcome(ana_mod, kind))
        kwargs = updated_with(report_cls)
        assert (
            kwargs["ai_status"] == "failed"
            and getattr(ana_mod.DispatchOutcomeType, kind).value in kwargs["ai_analysis"]
        )

    def test_no_report_ids_is_noop(self, ana_mod, task, report_cls):
        task.on_execute_complete({**ITEM, "report_ids": []}, self.outcome(ana_mod, "SUCCESS", "ok"))
        report_cls.objects.filter.assert_not_called()
