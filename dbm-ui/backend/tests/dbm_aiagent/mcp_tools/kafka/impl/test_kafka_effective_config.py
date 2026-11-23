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
import subprocess
from unittest.mock import patch

import pytest

from backend.dbm_aiagent.mcp_tools.kafka.impl import kafka_toolbox
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_effective_config import (
    HOUR_MS,
    MINUTE_MS,
    build_effective_config_result,
    compute_effective_config,
    parse_overrides,
    parse_static_properties,
    split_sections,
)

DOMAIN = "kafka.demo.test.db"
TOPIC = "demo_topic"


def _zk(entity, configs):
    body = ",".join(f"{k}={v}" for k, v in configs.items())
    return f"Configs for {entity} are {body}"


def _raw(static="", topic=None, dynamic=None, dynamic_default=None, end=True, broker_id="", client_props=""):
    """拼出脚本的原始输出；传 None 表示该段命令输出"没有覆盖项"的表头"""
    topic_text = _zk(f"topic '{TOPIC}'", topic or {})
    dynamic_text = _zk("broker 1001", dynamic or {})
    default_text = _zk("brokers in the cluster", dynamic_default or {}).replace("Configs for", "Default config for")
    parts = [
        "===STATIC===",
        static,
        "===CLIENT_PROPERTIES===",
        client_props,
        "===BROKER_ID===",
        broker_id,
        "===TOPIC===",
        topic_text,
        "===BROKER_DYNAMIC===",
        dynamic_text,
        "===BROKER_DEFAULT_DYNAMIC===",
        default_text,
    ]
    if end:
        parts.append("===END===")
    return "\n".join(parts)


def _build(raw, version="2.4.0"):
    return build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", version, raw)


def _effective(raw, name="retention_ms"):
    return _build(raw)["effective"][name]


class TestRetentionPriority:
    """一、保留期取值优先级"""

    def test_case1_all_default(self):
        item = _effective(_raw(static="broker.id=1001"))
        assert (item["value"], item["source"]) == (168 * HOUR_MS, "default")

    def test_case2_static_hours(self):
        item = _effective(_raw(static="broker.id=1001\nlog.retention.hours=72"))
        assert (item["value"], item["source"], item["key"]) == (72 * HOUR_MS, "broker_static", "log.retention.hours")
        assert item["hours"] == 72

    def test_case3_static_minutes_beats_hours(self):
        item = _effective(_raw(static="log.retention.hours=72\nlog.retention.minutes=30"))
        assert (item["value"], item["key"]) == (30 * MINUTE_MS, "log.retention.minutes")

    def test_case4_static_ms_beats_all(self):
        static = "log.retention.hours=72\nlog.retention.minutes=30\nlog.retention.ms=60000"
        item = _effective(_raw(static=static))
        assert (item["value"], item["key"]) == (60000, "log.retention.ms")

    def test_case5_topic_override_beats_static(self):
        item = _effective(_raw(static="log.retention.hours=168", topic={"retention.ms": "3600000"}))
        assert (item["value"], item["source"]) == (HOUR_MS, "topic")

    def test_case6_broker_dynamic_beats_static(self):
        item = _effective(_raw(static="log.retention.hours=168", dynamic={"log.retention.ms": "86400000"}))
        assert (item["value"], item["source"]) == (24 * HOUR_MS, "broker_dynamic")

    def test_case7_cluster_default_dynamic_beats_static(self):
        item = _effective(_raw(static="log.retention.hours=168", dynamic_default={"log.retention.ms": "86400000"}))
        assert (item["value"], item["source"]) == (24 * HOUR_MS, "broker_default_dynamic")

    def test_case8_broker_dynamic_beats_cluster_default_dynamic(self):
        raw = _raw(
            static="log.retention.hours=168",
            dynamic={"log.retention.ms": str(12 * HOUR_MS)},
            dynamic_default={"log.retention.ms": str(24 * HOUR_MS)},
        )
        item = _effective(raw)
        assert (item["value"], item["source"]) == (12 * HOUR_MS, "broker_dynamic")

    def test_case9_topic_beats_all_broker_layers(self):
        raw = _raw(
            static="log.retention.hours=168",
            topic={"retention.ms": str(HOUR_MS)},
            dynamic={"log.retention.ms": str(24 * HOUR_MS)},
        )
        item = _effective(raw)
        assert (item["value"], item["source"]) == (HOUR_MS, "topic")

    def test_case28_dynamic_ms_overrides_static_hours(self):
        raw = _raw(static="log.retention.hours=168", dynamic={"log.retention.ms": "3600000"})
        item = _effective(raw)
        assert (item["value"], item["source"]) == (HOUR_MS, "broker_dynamic")


class TestUnitsAndSpecialValues:
    """二、单位换算与特殊值"""

    def test_case11_topic_retention_minus_one_is_unlimited(self):
        item = _effective(_raw(topic={"retention.ms": "-1"}))
        assert item["value"] == -1 and item["unlimited"] is True and item["hours"] is None

    def test_case12_static_hours_minus_one_is_unlimited(self):
        item = _effective(_raw(static="log.retention.hours=-1"))
        assert item["value"] == -1 and item["unlimited"] is True

    def test_case13_retention_bytes_default_is_unlimited(self):
        item = _effective(_raw(), "retention_bytes")
        assert (item["value"], item["source"], item["unlimited"]) == (-1, "default", True)

    def test_case14_topic_retention_bytes_beats_static(self):
        item = _effective(
            _raw(static="log.retention.bytes=-1", topic={"retention.bytes": "1073741824"}), "retention_bytes"
        )
        assert (item["value"], item["source"], item["unlimited"]) == (1073741824, "topic", False)

    def test_case15_non_numeric_value_is_not_silently_skipped(self):
        result = _build(_raw(static="log.retention.hours=168", topic={"retention.ms": "abc"}))
        item = result["effective"]["retention_ms"]
        # 命中的层取值非法时不能回落到静态值，否则会给出看似正确的错误结论
        assert item["value"] is None and item["source"] == "topic" and item["parse_error"] is True
        assert any("retention_ms" in w for w in result["warnings"])


class TestSegmentAndRoll:
    """三、segment 与滚动"""

    def test_case16_defaults(self):
        effective = _build(_raw(static="broker.id=1001"))["effective"]
        assert effective["segment_bytes"]["value"] == 1073741824
        assert effective["roll_ms"]["value"] == 168 * HOUR_MS
        assert effective["cleanup_policy"]["value"] == "delete"
        assert effective["retention_check_interval_ms"]["value"] == 300000

    def test_case17_topic_segment_bytes(self):
        effective = _build(_raw(static="log.segment.bytes=1073741824", topic={"segment.bytes": "104857600"}))[
            "effective"
        ]
        assert (effective["segment_bytes"]["value"], effective["segment_bytes"]["source"]) == (104857600, "topic")

    def test_case18_topic_segment_ms_beats_static_roll(self):
        effective = _build(_raw(static="log.roll.hours=168", topic={"segment.ms": "3600000"}))["effective"]
        assert (effective["roll_ms"]["value"], effective["roll_ms"]["source"]) == (HOUR_MS, "topic")

    def test_case19_static_roll_ms_beats_roll_hours(self):
        effective = _build(_raw(static="log.roll.hours=24\nlog.roll.ms=3600000"))["effective"]
        assert (effective["roll_ms"]["value"], effective["roll_ms"]["key"]) == (HOUR_MS, "log.roll.ms")

    def test_compact_policy_is_reported(self):
        effective = _build(_raw(topic={"cleanup.policy": "compact"}))["effective"]
        assert (effective["cleanup_policy"]["value"], effective["cleanup_policy"]["source"]) == ("compact", "topic")

    def test_cleanup_policy_value_with_comma_is_kept(self):
        # cleanup.policy=delete,compact 中的逗号不能被当成配置项分隔符丢掉
        configs, recognized = parse_overrides(
            "Configs for topic 'x' are retention.ms=1000,cleanup.policy=delete,compact"
        )
        assert recognized and configs == {"retention.ms": "1000", "cleanup.policy": "delete,compact"}


class TestStaticFileParsing:
    """四、server.properties 解析"""

    def test_case21_spaces_around_equal(self):
        configs, _warnings = parse_static_properties("log.retention.hours = 72")
        assert configs == {"log.retention.hours": "72"}

    def test_case22_commented_line_ignored(self):
        configs, _warnings = parse_static_properties("#log.retention.hours=72\n! log.segment.bytes=1")
        assert configs == {}

    def test_case23_last_duplicate_wins(self):
        configs, _warnings = parse_static_properties("log.retention.hours=72\nlog.retention.hours=24")
        assert configs == {"log.retention.hours": "24"}

    def test_case24_empty_value_is_unconfigured_with_warning(self):
        configs, warnings = parse_static_properties("log.retention.hours=72\nlog.retention.hours=")
        assert configs == {}
        assert len(warnings) == 1

    def test_case25_trailing_cr_and_spaces(self):
        configs, _warnings = parse_static_properties("log.retention.hours=72  \r\nbroker.id=1001\r\n")
        assert configs == {"log.retention.hours": "72", "broker.id": "1001"}

    def test_case26_non_whitelist_keys_are_dropped(self):
        text = "listeners=SASL_PLAINTEXT://127.0.0.1:9092\nsasl.jaas.config=secret\nlog.retention.hours=72"
        configs, _warnings = parse_static_properties(text)
        assert configs == {"log.retention.hours": "72"}
        result = _build(_raw(static=text))
        assert "secret" not in str(result)

    def test_key_prefix_is_not_confused(self):
        # log.retention.ms 不能误取 log.retention.minutes 的值
        configs, _warnings = parse_static_properties("log.retention.minutes=30")
        assert "log.retention.ms" not in configs


class TestInvalidKeysAndIncompleteOutput:
    def test_case27_topic_invalid_key_ignored_with_warning(self):
        result = _build(_raw(static="log.retention.hours=168", topic={"retention.hours": "1"}))
        item = result["effective"]["retention_ms"]
        assert (item["value"], item["source"]) == (168 * HOUR_MS, "broker_static")
        assert any("retention.hours" in w for w in result["warnings"])

    def test_dynamic_hours_key_ignored_with_warning(self):
        result = _build(_raw(static="log.retention.ms=60000", dynamic={"log.retention.hours": "24"}))
        assert result["effective"]["retention_ms"]["source"] == "broker_static"
        assert any("log.retention.hours" in w for w in result["warnings"])

    def test_command_error_is_not_treated_as_no_override(self):
        raw = "===STATIC===\nlog.retention.hours=72\n===TOPIC===\nError while executing config command\n===END==="
        result = _build(raw)
        assert any("topic" in w for w in result["warnings"])

    def test_missing_end_marker_warns(self):
        result = _build(_raw(static="log.retention.hours=72", end=False))
        assert any("结束标记" in w or "end" in w.lower() for w in result["warnings"])

    def test_skipped_broker_dynamic_warns_instead_of_pretending_empty(self):
        raw = _raw(static="log.retention.hours=72").replace("Configs for broker 1001 are ", "SKIPPED")
        result = _build(raw)
        assert any("broker.id" in w for w in result["warnings"])

    def test_newer_version_warns_about_defaults(self):
        result = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "3.8.0", _raw(static="broker.id=1001"))
        assert any("3.8.0" in w for w in result["warnings"])

    def test_verified_version_has_no_version_warning(self):
        assert _build(_raw(static="broker.id=1001"), version="2.4.0")["warnings"] == []

    def test_result_shape(self):
        result = _build(_raw(static="broker.id=1001\nlog.retention.hours=72"))
        assert result["broker_id"] == "1001" and result["broker_ip"] == "127.0.0.1"
        assert result["layers"]["broker_static"] == {"log.retention.hours": "72"}
        assert set(result["layers"]) == {"topic", "broker_dynamic", "broker_default_dynamic", "broker_static"}


class TestOverrideFormats:
    def test_zk_format_with_overrides(self):
        configs, recognized = parse_overrides("Configs for topic 'x' are retention.ms=1000,segment.bytes=2048")
        assert recognized and configs == {"retention.ms": "1000", "segment.bytes": "2048"}

    def test_zk_format_without_overrides_is_recognized(self):
        configs, recognized = parse_overrides("Configs for topic 'x' are ")
        assert recognized and configs == {}

    def test_cluster_default_header(self):
        configs, recognized = parse_overrides("Default config for brokers in the cluster are log.retention.ms=1000")
        assert recognized and configs == {"log.retention.ms": "1000"}

    def test_bootstrap_server_format(self):
        text = (
            "Dynamic configs for topic x are:\n"
            "  retention.ms=1000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=1000}\n"
            "  cleanup.policy=compact sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:cleanup.policy=compact}\n"
        )
        configs, recognized = parse_overrides(text)
        assert recognized and configs == {"retention.ms": "1000", "cleanup.policy": "compact"}

    def test_error_output_is_not_recognized(self):
        _configs, recognized = parse_overrides("Exception in thread main: Connection refused")
        assert not recognized

    def test_empty_output_is_not_recognized(self):
        assert parse_overrides("")[1] is False


class TestSplitSections:
    def test_split(self):
        sections = split_sections("noise\n===STATIC===\na=1\n===TOPIC===\nb\n===END===\n")
        assert sections["STATIC"].strip() == "a=1" and sections["TOPIC"].strip() == "b"

    def test_unknown_marker_is_content(self):
        sections = split_sections("===STATIC===\n===FOO===\n===END===")
        assert "===FOO===" in sections["STATIC"]


def test_compute_effective_config_is_pure():
    result = compute_effective_config({}, {}, {}, {})
    assert result["retention_ms"]["source"] == "default"


@pytest.mark.parametrize("topic", ["a.b-c_d", "T1"])
def test_script_contains_whitelist_only_and_markers(topic):
    info = {"broker_ip": "127.0.0.1", "broker_port": 9092}
    script = kafka_toolbox.build_effective_config_script(info, topic)
    for marker in ("===STATIC===", "===TOPIC===", "===BROKER_DYNAMIC===", "===BROKER_DEFAULT_DYNAMIC===", "===END==="):
        assert marker in script
    assert f"--entity-name={topic} " in script
    assert "log\\.retention\\.hours" in script
    # 认证相关的键不在静态白名单里，只检查 STATIC 段的那条 grep
    static_grep = next(line for line in script.splitlines() if line.startswith("grep -E") and "PROPS" in line)
    assert "sasl" not in static_grep.lower() and "listeners" not in static_grep


def test_get_effective_topic_config_runs_single_job():
    info = {
        "broker_ip": "127.0.0.1",
        "broker_port": 9092,
        "bk_cloud_id": 0,
        "major_version": "2.4.0",
    }
    raw = _raw(static="broker.id=1001\nlog.retention.hours=168")
    with patch.object(kafka_toolbox, "resolve_cluster_connection_info", return_value=info), patch.object(
        kafka_toolbox, "execute_kafka_script", return_value=raw
    ) as mock_exec:
        result = kafka_toolbox.get_effective_topic_config(DOMAIN, TOPIC)
    assert mock_exec.call_count == 1
    assert result["effective"]["retention_ms"]["value"] == 168 * HOUR_MS
    assert result["warnings"] == []


@pytest.mark.parametrize("topic", ["a;rm -rf /", "a b", "$(id)", "a`id`", "a|b", "a\nb"])
def test_topic_with_shell_metacharacters_is_rejected(topic):
    # topic 会被拼进远程执行的脚本，必须在序列化器层拦住
    from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_toolbox import GetEffectiveTopicConfigInputSerializer

    slz = GetEffectiveTopicConfigInputSerializer(data={"cluster_domain": DOMAIN, "topic": topic})
    assert not slz.is_valid()
    assert "topic" in slz.errors


def test_valid_topic_is_accepted():
    from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_toolbox import GetEffectiveTopicConfigInputSerializer

    slz = GetEffectiveTopicConfigInputSerializer(data={"cluster_domain": DOMAIN, "topic": "a.b-c_d"})
    assert slz.is_valid(), slz.errors


class TestBrokerId:
    def test_auto_assigned_id_comes_from_broker_id_section(self):
        # 自动分配 id 的 broker，server.properties 里没有 broker.id
        result = _build(_raw(static="log.retention.hours=168", broker_id="1002"))
        assert result["broker_id"] == "1002"
        assert not any("broker.id" in w for w in result["warnings"])

    def test_section_wins_over_static(self):
        assert _build(_raw(static="broker.id=1001", broker_id="1002"))["broker_id"] == "1002"

    def test_falls_back_to_static_when_section_empty(self):
        assert _build(_raw(static="broker.id=1001"))["broker_id"] == "1001"

    def test_non_numeric_id_is_dropped(self):
        assert _build(_raw(broker_id="abc"))["broker_id"] is None

    def test_script_resolves_id_via_broker_api_versions_with_auth(self):
        info = {"broker_ip": "127.0.0.1", "broker_port": 9092}
        script = kafka_toolbox.build_effective_config_script(info, "t")
        assert "kafka-broker-api-versions.sh" in script and "meta.properties" not in script
        # 该命令只支持 bootstrap-server，SASL 集群上必须带认证参数，且不能依赖 kafka-configs 的 ZK 模式判断
        assert "BROKER_AUTH_ARG" in script and "--command-config" in script
        assert '$1 == hp && $2 == "(id:"' in script


class TestRealZkHeaders:
    """2.4 ZK 模式下 kafka-configs 的真实输出头（取自现网，行尾无空格）"""

    @pytest.mark.parametrize(
        "header",
        [
            "Configs for topic 'demo_topic' are",
            "Configs for brokers '1003' are",
            "Configs for default brokers are",
        ],
    )
    def test_empty_overrides_are_recognized(self, header):
        configs, recognized = parse_overrides(header)
        assert recognized and configs == {}

    def test_broker_header_with_overrides(self):
        configs, recognized = parse_overrides("Configs for brokers '1003' are log.retention.ms=3600000")
        assert recognized and configs == {"log.retention.ms": "3600000"}

    def test_full_real_output_has_no_warnings(self):
        raw = "\n".join(
            [
                "===STATIC===",
                "default.replication.factor=2",
                "log.cleanup.policy=delete",
                "log.retention.bytes=-1",
                "log.retention.check.interval.ms=300000",
                "log.retention.hours=168",
                "log.segment.bytes=1073741824",
                "num.partitions=120",
                "===BROKER_ID===",
                "1003",
                "===TOPIC===",
                "Configs for topic 'demo_topic' are",
                "===BROKER_DYNAMIC===",
                "Configs for brokers '1003' are",
                "===BROKER_DEFAULT_DYNAMIC===",
                "Configs for default brokers are",
                "===END===",
            ]
        )
        result = _build(raw)
        assert result["warnings"] == [] and result["broker_id"] == "1003"
        retention = result["effective"]["retention_ms"]
        assert (retention["value"], retention["source"]) == (168 * HOUR_MS, "broker_static")


class TestClientProperties:
    def test_missing_client_properties_gives_specific_warning_once(self):
        # 取不到 id 时脚本输出 SKIPPED
        raw = _raw(static="log.retention.hours=168", client_props="missing").replace(
            "Configs for broker 1001 are", "SKIPPED"
        )
        result = _build(raw)
        client_warnings = [w for w in result["warnings"] if "client.properties" in w]
        assert len(client_warnings) == 1
        # 已经给出具体原因，不再重复给"取不到 broker.id"的笼统提示
        assert not any("广播地址" in w for w in result["warnings"])

    def test_skipped_without_missing_file_keeps_generic_warning(self):
        raw = _raw(static="log.retention.hours=168", client_props="present").replace(
            "Configs for broker 1001 are", "SKIPPED"
        )
        warnings = _build(raw)["warnings"]
        assert any("广播地址" in w for w in warnings) and not any("client.properties" in w for w in warnings)

    @pytest.mark.parametrize("state", ["present", "not_required", ""])
    def test_other_states_have_no_client_properties_warning(self, state):
        result = _build(_raw(static="log.retention.hours=168", client_props=state, broker_id="1003"))
        assert not any("client.properties" in w for w in result["warnings"])

    def test_script_reports_client_properties_state(self):
        info = {"broker_ip": "127.0.0.1", "broker_port": 9092}
        script = kafka_toolbox.build_effective_config_script(info, "t")
        assert "===CLIENT_PROPERTIES===" in script and 'CLIENT_PROPS_STATE="missing"' in script


STATIC_REAL = "\n".join(
    [
        "default.replication.factor=2",
        "log.cleanup.policy=delete",
        "log.retention.bytes=-1",
        "log.retention.check.interval.ms=300000",
        "log.retention.hours=4",
        "log.segment.bytes=1073741824",
        "num.partitions=1",
    ]
)


class TestRealOutputsOtherVersions:
    """取自现网的 0.10.2（ZK）与 4.1（bootstrap-server + SASL）输出"""

    def test_v0102_empty_default_dynamic_is_not_a_warning(self):
        raw = "\n".join(
            [
                "===STATIC===",
                STATIC_REAL,
                "===CLIENT_PROPERTIES===",
                "not_required",
                "===BROKER_ID===",
                "1002",
                "===TOPIC===",
                "Configs for topic 'demo_topic' are",
                "===BROKER_DYNAMIC===",
                "Configs for brokers '1002' are",
                "===BROKER_DEFAULT_DYNAMIC===",
                "===END===",
            ]
        )
        result = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "0.10.2", raw)
        assert result["warnings"] == [] and result["broker_id"] == "1002"
        assert result["effective"]["retention_ms"]["value"] == 4 * HOUR_MS

    def test_v41_bootstrap_format(self):
        raw = "\n".join(
            [
                "===STATIC===",
                STATIC_REAL,
                "===CLIENT_PROPERTIES===",
                "present",
                "===BROKER_ID===",
                "4",
                "===TOPIC===",
                "Dynamic configs for topic demo_topic are:",
                "  retention.ms=7200000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=7200000}",
                "===BROKER_DYNAMIC===",
                "Dynamic configs for broker 4 are:",
                "===BROKER_DEFAULT_DYNAMIC===",
                "Default configs for brokers in the cluster are:",
                "  min.insync.replicas=1 sensitive=false synonyms={DYNAMIC_DEFAULT_BROKER_CONFIG:min.insync.replicas=1}",
                "===END===",
            ]
        )
        result = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "4.1.0", raw)
        item = result["effective"]["retention_ms"]
        assert (item["value"], item["source"]) == (2 * HOUR_MS, "topic")
        # 无关的动态项（min.insync.replicas）不进入返回
        assert result["layers"]["broker_default_dynamic"] == {}
        # 4.x 只有"默认值未核对"这一条版本提示
        assert len(result["warnings"]) == 1 and "4.1.0" in result["warnings"][0]

    def test_v41_empty_headers_are_recognized(self):
        for header in ("Dynamic configs for broker 4 are:", "Default configs for brokers in the cluster are:"):
            configs, recognized = parse_overrides(header)
            assert recognized and configs == {}

    def test_v41_missing_topic_gets_specific_warning(self):
        raw = "\n".join(
            [
                "===STATIC===",
                STATIC_REAL,
                "===TOPIC===",
                "The topic 'demo_topic' doesn't exist and doesn't have dynamic config.",
                "===BROKER_DYNAMIC===",
                "Dynamic configs for broker 4 are:",
                "===BROKER_DEFAULT_DYNAMIC===",
                "Default configs for brokers in the cluster are:",
                "===END===",
            ]
        )
        warnings = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "4.1.0", raw)["warnings"]
        assert any("不存在" in w and TOPIC in w for w in warnings)
        assert not any("没有得到可识别的输出" in w for w in warnings)

    def test_blank_topic_or_broker_section_still_warns(self):
        raw = "===STATIC===\nlog.retention.hours=4\n===TOPIC===\n===BROKER_DYNAMIC===\n===END==="
        warnings = _build(raw)["warnings"]
        assert any("topic" in w for w in warnings)


class TestV41RealTopicOutput:
    """取自现网 4.1 的存在的 topic 输出（含 synonyms 里带逗号的行）"""

    TOPIC_SECTION = "\n".join(
        [
            "Dynamic configs for topic demo_topic are:",
            "  cleanup.policy=delete sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:cleanup.policy=delete, "
            "STATIC_BROKER_CONFIG:log.cleanup.policy=delete, DEFAULT_CONFIG:log.cleanup.policy=delete}",
            "  max.message.bytes=104857600 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:max.message.bytes=104857600, "
            "STATIC_BROKER_CONFIG:message.max.bytes=104857600, DEFAULT_CONFIG:message.max.bytes=1048588}",
            "  min.insync.replicas=1 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:min.insync.replicas=1, "
            "DYNAMIC_DEFAULT_BROKER_CONFIG:min.insync.replicas=1, DEFAULT_CONFIG:min.insync.replicas=1}",
            "  retention.bytes=-1 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.bytes=-1, "
            "STATIC_BROKER_CONFIG:log.retention.bytes=-1, DEFAULT_CONFIG:log.retention.bytes=-1}",
            "  retention.ms=3600000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=3600000}",
        ]
    )

    def test_parse_picks_each_key_once(self):
        configs, recognized = parse_overrides(self.TOPIC_SECTION)
        assert recognized
        assert configs["retention.ms"] == "3600000" and configs["cleanup.policy"] == "delete"
        assert configs["retention.bytes"] == "-1" and configs["max.message.bytes"] == "104857600"

    def test_effective_retention_comes_from_topic(self):
        raw = "\n".join(
            [
                "===STATIC===",
                STATIC_REAL,
                "===CLIENT_PROPERTIES===",
                "present",
                "===BROKER_ID===",
                "4",
                "===TOPIC===",
                self.TOPIC_SECTION,
                "===BROKER_DYNAMIC===",
                "Dynamic configs for broker 4 are:",
                "===BROKER_DEFAULT_DYNAMIC===",
                "Default configs for brokers in the cluster are:",
                "  min.insync.replicas=1 sensitive=false synonyms={DYNAMIC_DEFAULT_BROKER_CONFIG:min.insync.replicas=1}",
                "===END===",
            ]
        )
        result = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "4.1.0", raw)
        item = result["effective"]["retention_ms"]
        assert (item["value"], item["source"]) == (HOUR_MS, "topic")
        assert result["effective"]["retention_bytes"]["source"] == "topic"
        # 静态值是 4 小时，topic 覆盖为 1 小时，原始静态层仍然保留用于核对
        assert result["layers"]["broker_static"]["log.retention.hours"] == "4"
        assert len(result["warnings"]) == 1 and "4.1.0" in result["warnings"][0]


class TestReviewFixes:
    def test_end_marker_must_be_its_own_line(self):
        # topic 名或报错里含 END 不能被当成脚本完整结束
        raw = "===STATIC===\nlog.retention.hours=4\n===TOPIC===\nConfigs for topic 'BACKEND_EVENTS' are\n"
        assert any("结束标记" in w for w in _build(raw)["warnings"])

    def test_empty_default_dynamic_warns_on_24(self):
        raw = _raw(static="log.retention.hours=4", dynamic_default=None).replace(
            "Default config for brokers in the cluster are ", ""
        )
        assert any("broker_default_dynamic" in w for w in _build(raw)["warnings"])

    def test_empty_default_dynamic_ok_only_on_legacy(self):
        raw = _raw(static="log.retention.hours=4").replace("Default config for brokers in the cluster are ", "")
        assert build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", "0.10.2", raw)["warnings"] == []

    @pytest.mark.parametrize("version", ["0.10.2", "1.0.0", "1.1.0", "2.4.0", "4.1.0", "unknown"])
    def test_missing_default_dynamic_section_always_warns(self, version):
        raw = _raw(static="log.retention.hours=4").replace(
            "===BROKER_DEFAULT_DYNAMIC===\nDefault config for brokers in the cluster are \n", ""
        )
        warnings = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", version, raw)["warnings"]
        assert any("broker_default_dynamic" in warning for warning in warnings)

    @pytest.mark.parametrize("version", ["1.1.0", "2.4.0", "4.1.0", "unknown"])
    def test_present_empty_default_dynamic_section_warns_on_nonlegacy(self, version):
        raw = _raw(static="log.retention.hours=4").replace("Default config for brokers in the cluster are ", "")
        warnings = build_effective_config_result(DOMAIN, TOPIC, "127.0.0.1", version, raw)["warnings"]
        assert any("broker_default_dynamic" in warning for warning in warnings)

    def test_negative_retention_bytes_is_unlimited(self):
        item = _effective(_raw(topic={"retention.bytes": "-2"}), "retention_bytes")
        assert item["value"] == -1 and item["unlimited"] is True

    def test_script_filter_does_not_drop_topic_lines(self):
        script = kafka_toolbox.build_effective_config_script(
            {"broker_ip": "127.0.0.1", "broker_port": 9092}, "stray_events"
        )
        assert 'grep -v "stray"' not in script and "warning: stray" in script
        assert "--entity-name=stray_events " in script
        filter_assignment = next(line for line in script.splitlines() if line.startswith("FILTER="))
        topic_output = "Configs for topic 'stray_events' are retention.ms=3600000\n"
        output = subprocess.run(
            ["bash", "-c", filter_assignment + '\neval "$FILTER"'],
            input="egrep: warning: stray \\ before -\nSLF4J: noise\n" + topic_output,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert output == topic_output
        raw = _raw(static="log.retention.hours=168").replace(f"Configs for topic '{TOPIC}' are ", output.rstrip("\n"))
        result = _build(raw)
        assert result["effective"]["retention_ms"]["value"] == HOUR_MS
        assert result["effective"]["retention_ms"]["source"] == "topic"
        assert result["warnings"] == []

    def test_script_ignores_commented_sasl_and_falls_back_to_static_id(self):
        script = kafka_toolbox.build_effective_config_script({"broker_ip": "127.0.0.1", "broker_port": 9092}, "t")
        assert "SASL_ENABLED" in script and "grep -q 'SASL_PLAINTEXT'" not in script
        assert "broker\\.id[[:space:]]*=" in script

    def test_script_builder_rejects_bad_topic(self):
        with pytest.raises(ValueError):
            kafka_toolbox.build_effective_config_script({"broker_ip": "127.0.0.1", "broker_port": 9092}, "a;id")

    def test_output_serializer_contract(self):
        from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_toolbox import EffectiveTopicConfigOutputSerializer

        slz = EffectiveTopicConfigOutputSerializer(data=_build(_raw(static="broker.id=1001", broker_id="1001")))
        assert slz.is_valid(), slz.errors


class TestPrReviewRound2:
    def test_empty_cleanup_policy_does_not_shadow_static(self):
        result = _build(_raw(static="log.cleanup.policy=compact", topic={"cleanup.policy": ""}))
        item = result["effective"]["cleanup_policy"]
        assert (item["value"], item["source"]) == ("compact", "broker_static")
        assert any("cleanup.policy" in w and "为空" in w for w in result["warnings"])

    def test_empty_retention_ms_falls_through_with_warning(self):
        result = _build(_raw(static="log.retention.hours=4", topic={"retention.ms": ""}))
        assert result["effective"]["retention_ms"]["source"] == "broker_static"
        assert any("retention.ms" in w for w in result["warnings"])

    def test_leading_dash_topic_uses_equals_form(self):
        info = {"broker_ip": "127.0.0.1", "broker_port": 9092}
        script = kafka_toolbox.build_effective_config_script(info, "-foo")
        assert "--entity-name=-foo " in script and "--entity-name -foo" not in script

    @pytest.mark.parametrize(
        "builder",
        [
            lambda: kafka_toolbox.build_kafka_cli_script(
                {"broker_ip": "127.0.0.1", "broker_port": 9092}, "kafka-topics.sh", "--list"
            ),
        ],
    )
    def test_old_script_filter_is_anchored(self, builder):
        assert 'grep -v "stray"' not in builder() and 'grep -v "warning: stray"' in builder()

    def test_all_filters_in_module_are_anchored(self):
        import inspect

        code_lines = [ln for ln in inspect.getsource(kafka_toolbox).splitlines() if not ln.lstrip().startswith("#")]
        assert not any('grep -v "stray"' in ln for ln in code_lines)
