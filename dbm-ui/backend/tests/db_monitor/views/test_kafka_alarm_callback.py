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
import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.db_monitor.views.callbacks import kafka as kafka_callback
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.db_monitor.views.callbacks.kafka import KafkaAlarm, call_kafka_alarm_analyzer
from backend.db_monitor.views.callbacks.mysql import MySQLAlarm
from backend.db_monitor.views.callbacks.redis import RedisAlarm
from backend.dbm_aiagent.agent.commands import CommandProcessor
from backend.dbm_aiagent.agent.constants import DBMAgentCode

CLUSTER_DOMAIN = "kafka.test.db"

CALLBACK_DATA = {
    "appointees": ["admin", "leader"],
    "callback_message": {
        "current_value": "91.5",
        "description": "磁盘空间使用率 >= 90%",
        "type": "alarm",
        "latest_anomaly_record": {
            "create_time": "2026-10-14 01:00:00",
            "origin_alarm": {
                "anomaly": {"1": {"anomaly_message": "当前值 91.5%", "anomaly_time": "2026-10-14 01:00:00"}}
            },
        },
        "event": {
            "level": 1,
            "begin_time": "2026-10-14 00:55:00",
            "create_time": "2026-10-14 00:55:00",
            "agg_dimensions": ["cluster_domain"],
            "dimensions": {
                "appid": "3",
                "cluster_domain": CLUSTER_DOMAIN,
                "cluster_type": "kafka",
                "bk_target_ip": "1.1.1.1",
            },
        },
        "strategy": {"name": "Kafka 主机磁盘空间使用率"},
        "related_info": {},
    },
}

ALARM_BASE_INFO = {
    "bk_biz_id": 3,
    "cluster_type": "kafka",
    "cluster_domain": CLUSTER_DOMAIN,
    "dimensions": {},
    "strategy_name": "Kafka 主机磁盘空间使用率",
    "level": 1,
    "alarm_time": "2026-10-14 09:00:00+0800",
    "appointees": ["admin", "leader"],
}


def make_callback_data(strategy_name=None, level=None, dimensions=None):
    data = copy.deepcopy(CALLBACK_DATA)
    message = data["callback_message"]
    if strategy_name is not None:
        message["strategy"]["name"] = strategy_name
    if level is not None:
        message["event"]["level"] = level
    if dimensions is not None:
        message["event"]["dimensions"] = dimensions
    return data


@pytest.fixture
def mock_handler():
    """拦截异步任务派发，同时放开频率限制"""
    handler = MagicMock()
    with patch.dict(kafka_callback.__dict__, {"call_kafka_alarm_analyzer": handler}):
        with patch.object(AlarmCallback, "check_rate_limit", return_value=True):
            yield handler


class TestKafkaAlarmMatch:
    @pytest.mark.parametrize(
        "strategy_name, level, expect_dispatch",
        [
            # 磁盘：致命、预警都触发
            ("Kafka 主机磁盘空间使用率", 1, True),
            ("Kafka 主机磁盘空间使用率", 2, True),
            ("Kafka 主机磁盘空间使用率", 3, False),
            # 业务自建策略名带前缀也能命中
            ("DBM#test Kafka 主机磁盘空间使用率", 1, True),
            # 副本不同步、CPU：只接预警。策略名取自模板顶层 name，不是文件名
            ("Kafka under replicated partitions", 2, True),
            ("Kafka under replicated partitions", 1, False),
            ("DBM#test Kafka under replicated partitions", 2, True),
            ("KAFKA UNDER REPLICATED PARTITIONS", 2, True),
            ("Kafka 主机 CPU 使用率", 2, True),
            ("Kafka 主机 CPU 使用率", 1, False),
            # 消费组延迟：不限制级别
            ("Kafka 消费组延迟", 1, True),
            ("Kafka 消费组延迟", 2, True),
            ("Kafka 消费组延迟", 3, True),
            # 本次不分析的策略
            ("Kafka OfflinePartitions", 2, False),
            ("Kafka AbnormalControllerState", 2, False),
            ("MySQL 主机 CPU 负载", 2, False),
        ],
    )
    def test_match(self, mock_handler, strategy_name, level, expect_dispatch):
        data = make_callback_data(strategy_name=strategy_name, level=level)
        KafkaAlarm.callback(data)
        assert mock_handler.delay.called is expect_dispatch

    def test_dispatch_args(self, mock_handler):
        KafkaAlarm.callback(make_callback_data())
        callback_data, alarm_base_info = mock_handler.delay.call_args[0]
        assert callback_data["callback_message"]["strategy"]["name"] == "Kafka 主机磁盘空间使用率"
        assert alarm_base_info["cluster_domain"] == CLUSTER_DOMAIN
        assert alarm_base_info["bk_biz_id"] == 3
        assert alarm_base_info["cluster_type"] == "kafka"
        assert alarm_base_info["level"] == 1
        assert alarm_base_info["appointees"] == ["admin", "leader"]
        # 推送消息渲染需要的字段都在
        for key in ["strategy_name", "alarm_time", "cluster_domain", "cluster_type", "level"]:
            assert key in alarm_base_info
        # 告警时间转成东八区
        assert alarm_base_info["alarm_time"].startswith("2026-10-14 09:00:00")

    @pytest.mark.parametrize(
        "raw_level, strategy_name, expect_dispatch, expect_level",
        [
            # 字符串级别也要能命中带级别限制的规则
            ("1", "Kafka 主机磁盘空间使用率", True, 1),
            ("2", "Kafka 主机磁盘空间使用率", True, 2),
            ("3", "Kafka 主机磁盘空间使用率", False, 3),
            ("1", "Kafka under replicated partitions", False, 1),
            ("2", "Kafka under replicated partitions", True, 2),
            (2.0, "Kafka 主机 CPU 使用率", True, 2),
            # 无法解析：按不限制级别处理（与 RedisAlarm 一致），不抛异常
            ("abc", "Kafka under replicated partitions", True, None),
            ("", "Kafka 主机 CPU 使用率", True, None),
            (None, "Kafka 主机 CPU 使用率", True, None),
        ],
    )
    def test_event_level_normalized(self, mock_handler, raw_level, strategy_name, expect_dispatch, expect_level):
        data = make_callback_data(strategy_name=strategy_name)
        data["callback_message"]["event"]["level"] = raw_level
        KafkaAlarm.callback(data)
        assert mock_handler.delay.called is expect_dispatch
        if expect_dispatch:
            assert mock_handler.delay.call_args[0][1]["level"] == expect_level

    def test_rate_limited(self):
        handler = MagicMock()
        with patch.dict(kafka_callback.__dict__, {"call_kafka_alarm_analyzer": handler}):
            with patch.object(AlarmCallback, "check_rate_limit", return_value=False) as limit:
                KafkaAlarm.callback(make_callback_data())
        assert not handler.delay.called
        limit.assert_called_once_with(CLUSTER_DOMAIN, "call_kafka_alarm_analyzer", "磁盘空间使用率", "1 / 8")

    def test_missing_handler_does_not_raise(self):
        with patch.dict(kafka_callback.__dict__, {"call_kafka_alarm_analyzer": None}):
            with patch.object(AlarmCallback, "check_rate_limit", return_value=True):
                KafkaAlarm.callback(make_callback_data())

    def test_backfill_biz_and_type_from_cluster(self, mock_handler):
        """维度里没有 appid、cluster_type 时，通过集群记录补齐"""
        cluster = MagicMock(cluster_type="kafka", bk_biz_id=77)
        data = make_callback_data(dimensions={"cluster_domain": CLUSTER_DOMAIN})
        with patch.object(kafka_callback.Cluster, "objects") as objects:
            objects.filter.return_value.first.return_value = cluster
            KafkaAlarm.callback(data)
        alarm_base_info = mock_handler.delay.call_args[0][1]
        assert alarm_base_info["bk_biz_id"] == 77
        assert alarm_base_info["cluster_type"] == "kafka"

    def test_cluster_not_found_does_not_raise(self, mock_handler):
        """集群查不到时不抛异常（MySQL 版本在这里会空指针）"""
        data = make_callback_data(dimensions={"cluster_domain": CLUSTER_DOMAIN})
        with patch.object(kafka_callback.Cluster, "objects") as objects:
            objects.filter.return_value.first.return_value = None
            KafkaAlarm.callback(data)
        alarm_base_info = mock_handler.delay.call_args[0][1]
        assert alarm_base_info["bk_biz_id"] == 0
        assert alarm_base_info["cluster_type"] == ""

    def test_invalid_appid(self, mock_handler):
        data = make_callback_data(
            dimensions={"appid": "abc", "cluster_domain": CLUSTER_DOMAIN, "cluster_type": "kafka"}
        )
        with patch.object(kafka_callback.Cluster, "objects") as objects:
            objects.filter.return_value.first.return_value = MagicMock(cluster_type="kafka", bk_biz_id=5)
            KafkaAlarm.callback(data)
        assert mock_handler.delay.call_args[0][1]["bk_biz_id"] == 5


class TestKafkaRealTemplateNames:
    """
    用仓库里真实的策略模板校验匹配规则。
    同步到监控平台的策略名取自模板顶层 name 字段（见 MonitorPolicy.sync_plat_monitor_policy），
    不是文件名，二者可能不同（例如 Kafka UnderReplicatedPartitions.json 的 name 是
    "Kafka under replicated partitions"）。测试里手写策略名会漏掉这类偏差，所以这里直接读模板。
    """

    TPL_DIR = Path(__file__).resolve().parents[3] / "db_monitor" / "tpls" / "alarm" / "kafka"

    # 以模板文件名（不含后缀）为 key：期望哪些告警级别会触发 AI 分析；不在表里的模板不应触发
    EXPECTED_TRIGGER_LEVELS = {
        "Kafka 主机磁盘空间使用率": {1, 2},
        "Kafka UnderReplicatedPartitions": {2},
        "Kafka 主机 CPU 使用率": {2},
        "Kafka 消费组延迟": {1, 2, 3},
    }

    @classmethod
    def load_templates(cls):
        return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(cls.TPL_DIR.glob("*.json"))}

    @staticmethod
    def triggered_levels(strategy_name):
        conditions = KafkaAlarm.STRATEGY_HANDLERS["call_kafka_alarm_analyzer"]
        return {
            level
            for level in (1, 2, 3)
            if any(KafkaAlarm._is_match(cond, strategy_name, level, "kafka") for cond in conditions)
        }

    def test_expected_templates_exist(self):
        """期望接入的模板必须真实存在，避免模板改名或删除后测试悄悄变成空跑"""
        assert set(self.EXPECTED_TRIGGER_LEVELS) <= set(self.load_templates())

    @staticmethod
    def group_by_dimensions(tpl):
        """指标型模板的分组维度在 agg_dimension 里；PromQL 型模板写在表达式的 by (...) 里"""
        query_config = tpl["details"]["items"][0]["query_configs"][0]
        return query_config.get("agg_dimension") or query_config.get("promql", "")

    def test_triggering_templates_carry_cluster_domain(self):
        """handler 靠告警维度里的 cluster_domain 定位集群，接入的模板必须把它带到告警事件里"""
        templates = self.load_templates()
        for stem in self.EXPECTED_TRIGGER_LEVELS:
            dimensions = self.group_by_dimensions(templates[stem])
            assert "cluster_domain" in dimensions, f"模板 {stem!r} 的分组维度缺少 cluster_domain"

    def test_every_template_matches_expectation(self):
        templates = self.load_templates()
        assert templates, "没有读到任何 Kafka 策略模板"
        for stem, tpl in templates.items():
            expected = self.EXPECTED_TRIGGER_LEVELS.get(stem, set())
            actual = self.triggered_levels(tpl["name"])
            assert actual == expected, f"模板 {stem!r}（策略名 {tpl['name']!r}）触发级别应为 {expected}，实际 {actual}"

    @pytest.mark.parametrize("stem", sorted(EXPECTED_TRIGGER_LEVELS))
    def test_dispatch_with_real_policy_name(self, mock_handler, stem):
        """用模板里的真实策略名走完整的 callback，最低级别能派发，不在期望里的级别不派发"""
        name = self.load_templates()[stem]["name"]
        for level in (1, 2, 3):
            mock_handler.reset_mock()
            KafkaAlarm.callback(make_callback_data(strategy_name=name, level=level))
            assert mock_handler.delay.called is (level in self.EXPECTED_TRIGGER_LEVELS[stem])


class TestAlarmDispatch:
    """经过 AlarmCallback.dispatch 的分发：集群类型过滤、周末跳过"""

    @pytest.mark.parametrize(
        "cluster_type, kafka_called",
        [("kafka", True), ("tendbha", False), ("redis_cluster", False)],
    )
    def test_cluster_type_filter(self, cluster_type, kafka_called):
        data = make_callback_data(
            dimensions={"appid": "3", "cluster_domain": CLUSTER_DOMAIN, "cluster_type": cluster_type}
        )
        with patch.object(AlarmCallback, "skip_by_weekend", return_value=False), patch.object(
            KafkaAlarm, "callback"
        ) as kafka_cb, patch.object(MySQLAlarm, "callback"), patch.object(RedisAlarm, "callback"):
            AlarmCallback.dispatch(data)
        assert kafka_cb.called is kafka_called

    def test_weekend_skip(self):
        with patch.object(AlarmCallback, "skip_by_weekend", return_value=True), patch.object(
            KafkaAlarm, "callback"
        ) as kafka_cb:
            AlarmCallback.dispatch(make_callback_data())
        assert not kafka_cb.called


class TestCallKafkaAlarmAnalyzer:
    @pytest.fixture
    def env_on(self):
        with patch.object(kafka_callback.env, "ENABLE_DBM_AI", True):
            yield

    @pytest.fixture
    def kafka_cluster_exists(self):
        with patch.object(kafka_callback.Cluster, "objects") as objects:
            objects.filter.return_value.exists.return_value = True
            yield objects

    @pytest.fixture
    def agent(self):
        with patch("backend.dbm_aiagent.agent.handlers.AgentHandler.ask_agent_with_content") as ask:
            yield ask

    @pytest.fixture
    def notify(self):
        with patch.object(kafka_callback.NotifyAdapter, "send_msg_for_ai_report") as send:
            yield send

    def run_task(self, base_info=None):
        call_kafka_alarm_analyzer(copy.deepcopy(CALLBACK_DATA), base_info or dict(ALARM_BASE_INFO))

    def test_disabled(self, agent, notify):
        with patch.object(kafka_callback.env, "ENABLE_DBM_AI", False):
            self.run_task()
        assert not agent.called
        assert not notify.called

    def test_no_cluster_domain(self, env_on, agent, notify):
        self.run_task(dict(ALARM_BASE_INFO, cluster_domain=""))
        assert not agent.called
        assert not notify.called

    def test_not_kafka_cluster(self, env_on, agent, notify):
        with patch.object(kafka_callback.Cluster, "objects") as objects:
            objects.filter.return_value.exists.return_value = False
            self.run_task()
        assert not agent.called
        assert not notify.called

    def test_success(self, env_on, kafka_cluster_exists, agent, notify):
        agent.return_value = "结论：Topic 保留策略问题"
        self.run_task()

        kwargs = agent.call_args.kwargs
        assert kwargs["agent_code"] == DBMAgentCode.KAFKA_INSPECT
        assert "kafka_alarm_analyzer" in kwargs["content"]
        assert "1800" in kwargs["content"]
        # 查的是 Kafka 集群
        filter_kwargs = kafka_cluster_exists.filter.call_args.kwargs
        assert filter_kwargs == {"immute_domain": CLUSTER_DOMAIN, "cluster_type": "kafka"}

        push = notify.call_args.kwargs
        assert push["bk_biz_id"] == 3
        assert push["receivers"] == ["admin", "leader"]
        assert push["ai_result"] == "结论：Topic 保留策略问题"
        assert push["share_url"] == ""
        assert CLUSTER_DOMAIN in push["title"]
        assert "Kafka" in push["title"]
        assert push["base_info"]["strategy_name"] == "Kafka 主机磁盘空间使用率"

    def test_agent_returns_empty(self, env_on, kafka_cluster_exists, agent, notify):
        agent.return_value = ""
        self.run_task()
        assert not notify.called

    def test_agent_raises(self, env_on, kafka_cluster_exists, agent, notify):
        agent.side_effect = RuntimeError("agent down")
        self.run_task()  # 不外抛
        assert not notify.called

    def test_notify_raises(self, env_on, kafka_cluster_exists, agent, notify):
        agent.return_value = "ok"
        notify.side_effect = RuntimeError("send failed")
        self.run_task()  # 不外抛

    def test_long_output_uses_summary_url(self, env_on, kafka_cluster_exists, agent, notify):
        """输出过长走摘要；摘要 agent 返回了 share_url 就不再写报告"""
        agent.side_effect = [
            "x" * 3000,
            '<output>{"share_url": "http://dbm/ai-chat/share/abc/", "summary": "简短结论"}</output>',
        ]
        with patch("backend.db_report.models.ai_analysis_report.AiAnalysisReport") as report:
            self.run_task()

        assert agent.call_count == 2
        assert agent.call_args_list[0].kwargs["agent_code"] == DBMAgentCode.KAFKA_INSPECT
        assert agent.call_args_list[1].kwargs["agent_code"] == DBMAgentCode.DBM_AGENT_SUMMARY
        assert not report.objects.create.called
        push = notify.call_args.kwargs
        assert push["ai_result"] == "简短结论"
        assert push["share_url"] == "http://dbm/ai-chat/share/abc/"

    def test_long_output_writes_report(self, env_on, kafka_cluster_exists, agent, notify):
        """摘要没带 share_url 时，把原文写入报告并生成链接"""
        agent.side_effect = ["x" * 3000, '<output>{"share_url": "", "summary": "简短结论"}</output>']
        with patch("backend.db_report.models.ai_analysis_report.AiAnalysisReport") as report:
            report.objects.create.return_value = MagicMock(id="rid-1")
            self.run_task()

        create_kwargs = report.objects.create.call_args.kwargs
        assert create_kwargs["ai_agent"] == DBMAgentCode.KAFKA_INSPECT
        assert create_kwargs["cluster_domain"] == CLUSTER_DOMAIN
        assert create_kwargs["summary"] == "简短结论"
        assert "Kafka" in create_kwargs["title"]
        push = notify.call_args.kwargs
        assert push["share_url"].endswith("/ai-chat/share/rid-1/")

    def test_summary_agent_fails_falls_back(self, env_on, kafka_cluster_exists, agent, notify):
        """摘要 agent 异常时降级：用原文推送，仍写报告"""
        agent.side_effect = ["x" * 3000, RuntimeError("summary down")]
        with patch("backend.db_report.models.ai_analysis_report.AiAnalysisReport") as report:
            report.objects.create.return_value = MagicMock(id="rid-2")
            self.run_task()
        push = notify.call_args.kwargs
        assert push["ai_result"] == "x" * 3000
        assert push["share_url"].endswith("/ai-chat/share/rid-2/")

    def test_write_report_fails_still_notifies(self, env_on, kafka_cluster_exists, agent, notify):
        agent.side_effect = ["x" * 3000, '<output>{"share_url": "", "summary": "简短结论"}</output>']
        with patch("backend.db_report.models.ai_analysis_report.AiAnalysisReport") as report:
            report.objects.create.side_effect = RuntimeError("db down")
            self.run_task()
        push = notify.call_args.kwargs
        assert push["ai_result"] == "简短结论"
        assert push["share_url"] == ""


class TestKafkaAlarmCommand:
    def test_registered(self):
        handler = CommandProcessor._handlers["kafka_alarm_analyzer"]
        assert handler.agent_code == DBMAgentCode.KAFKA_INSPECT

    def test_render(self):
        rendered = CommandProcessor.process_command(
            {
                "command": "kafka_alarm_analyzer",
                "context": [{"__key": "alarm_content", "__value": "磁盘使用率 91%", "context_type": "text"}],
            }
        )
        assert "磁盘使用率 91%" in rendered
        assert "/kafka_alarm_analyzer" in rendered
        assert "1800" in rendered

    def test_agent_code_value(self):
        assert DBMAgentCode.KAFKA_INSPECT.value == "ai-kafka-inspect"
