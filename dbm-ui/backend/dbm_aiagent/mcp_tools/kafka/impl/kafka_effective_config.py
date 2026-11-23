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
import re
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext_lazy as _

"""
Kafka topic 有效配置：把 topic 覆盖项、broker 动态覆盖项、server.properties 静态值、内置默认值合并成最终生效值。

优先级（先命中先生效）：
    topic 覆盖 > broker 动态（本机） > broker 动态（集群默认） > server.properties 静态值 > 内置默认值

两级的键不对称：
    - topic 级只有 retention.ms，没有 retention.hours / retention.minutes
    - broker 动态层只能改 log.retention.ms / log.roll.ms，没有 hours / minutes 形式
    - ms > minutes > hours 的优先级只在 server.properties 内部用
"""

SECTION_STATIC = "STATIC"
SECTION_CLIENT_PROPERTIES = "CLIENT_PROPERTIES"
SECTION_BROKER_ID = "BROKER_ID"
SECTION_TOPIC = "TOPIC"
SECTION_BROKER_DYNAMIC = "BROKER_DYNAMIC"
SECTION_BROKER_DEFAULT_DYNAMIC = "BROKER_DEFAULT_DYNAMIC"
SECTION_END = "END"
SECTIONS = (
    SECTION_STATIC,
    SECTION_CLIENT_PROPERTIES,
    SECTION_BROKER_ID,
    SECTION_TOPIC,
    SECTION_BROKER_DYNAMIC,
    SECTION_BROKER_DEFAULT_DYNAMIC,
    SECTION_END,
)
# 脚本跳过某一段查询时写入该段的标记
SKIPPED_MARK = "SKIPPED"
# 脚本检测到集群启用了 SASL 但 client.properties 不存在时写入 CLIENT_PROPERTIES 段的状态
CLIENT_PROPS_MISSING = "missing"

LAYER_TOPIC = "topic"
LAYER_BROKER_DYNAMIC = "broker_dynamic"
LAYER_BROKER_DEFAULT_DYNAMIC = "broker_default_dynamic"
LAYER_BROKER_STATIC = "broker_static"
LAYER_DEFAULT = "default"

MINUTE_MS = 60 * 1000
HOUR_MS = 60 * MINUTE_MS

# server.properties 只回传白名单内的键，其余（认证、密码等）一律不读取、不返回
STATIC_WHITELIST = (
    "broker.id",
    "log.retention.ms",
    "log.retention.minutes",
    "log.retention.hours",
    "log.retention.bytes",
    "log.segment.bytes",
    "log.roll.ms",
    "log.roll.hours",
    "log.cleanup.policy",
    "log.retention.check.interval.ms",
    "num.partitions",
    "default.replication.factor",
)
TOPIC_KEYS = ("retention.ms", "retention.bytes", "segment.bytes", "segment.ms", "cleanup.policy")
DYNAMIC_KEYS = (
    "log.retention.ms",
    "log.retention.bytes",
    "log.segment.bytes",
    "log.roll.ms",
    "log.cleanup.policy",
)
# 这些键在对应层不可能出现，出现了就忽略并告警，避免被当成覆盖项
TOPIC_INVALID_KEYS = ("retention.hours", "retention.minutes", "segment.hours")
DYNAMIC_INVALID_KEYS = ("log.retention.minutes", "log.retention.hours", "log.roll.hours")

# 内置默认值（2.4 及以下一致）
DEFAULT_RETENTION_MS = 168 * HOUR_MS
DEFAULT_RETENTION_BYTES = -1
DEFAULT_SEGMENT_BYTES = 1024 * 1024 * 1024
DEFAULT_ROLL_MS = 168 * HOUR_MS
DEFAULT_CLEANUP_POLICY = "delete"
DEFAULT_RETENTION_CHECK_INTERVAL_MS = 300000

# 默认值只核对过 2.4 及以下，更高版本返回提示
MAX_VERIFIED_VERSION = (2, 4)

# 取值类型
KIND_RETENTION_MS = "retention_ms"  # 负数统一视为 -1（无限保留）
KIND_INT = "int"
KIND_STR = "str"

# 有效值各项：(类型, 默认值, 按优先级排列的候选 [(层, 键, 换算成目标单位的倍数)])
_EFFECTIVE_ITEMS = {
    "retention_ms": (
        KIND_RETENTION_MS,
        DEFAULT_RETENTION_MS,
        [
            (LAYER_TOPIC, "retention.ms", 1),
            (LAYER_BROKER_DYNAMIC, "log.retention.ms", 1),
            (LAYER_BROKER_DEFAULT_DYNAMIC, "log.retention.ms", 1),
            (LAYER_BROKER_STATIC, "log.retention.ms", 1),
            (LAYER_BROKER_STATIC, "log.retention.minutes", MINUTE_MS),
            (LAYER_BROKER_STATIC, "log.retention.hours", HOUR_MS),
        ],
    ),
    "retention_bytes": (
        KIND_INT,
        DEFAULT_RETENTION_BYTES,
        [
            (LAYER_TOPIC, "retention.bytes", 1),
            (LAYER_BROKER_DYNAMIC, "log.retention.bytes", 1),
            (LAYER_BROKER_DEFAULT_DYNAMIC, "log.retention.bytes", 1),
            (LAYER_BROKER_STATIC, "log.retention.bytes", 1),
        ],
    ),
    "segment_bytes": (
        KIND_INT,
        DEFAULT_SEGMENT_BYTES,
        [
            (LAYER_TOPIC, "segment.bytes", 1),
            (LAYER_BROKER_DYNAMIC, "log.segment.bytes", 1),
            (LAYER_BROKER_DEFAULT_DYNAMIC, "log.segment.bytes", 1),
            (LAYER_BROKER_STATIC, "log.segment.bytes", 1),
        ],
    ),
    "roll_ms": (
        KIND_INT,
        DEFAULT_ROLL_MS,
        [
            (LAYER_TOPIC, "segment.ms", 1),
            (LAYER_BROKER_DYNAMIC, "log.roll.ms", 1),
            (LAYER_BROKER_DEFAULT_DYNAMIC, "log.roll.ms", 1),
            (LAYER_BROKER_STATIC, "log.roll.ms", 1),
            (LAYER_BROKER_STATIC, "log.roll.hours", HOUR_MS),
        ],
    ),
    "cleanup_policy": (
        KIND_STR,
        DEFAULT_CLEANUP_POLICY,
        [
            (LAYER_TOPIC, "cleanup.policy", 1),
            (LAYER_BROKER_DYNAMIC, "log.cleanup.policy", 1),
            (LAYER_BROKER_DEFAULT_DYNAMIC, "log.cleanup.policy", 1),
            (LAYER_BROKER_STATIC, "log.cleanup.policy", 1),
        ],
    ),
    "retention_check_interval_ms": (
        KIND_INT,
        DEFAULT_RETENTION_CHECK_INTERVAL_MS,
        [(LAYER_BROKER_STATIC, "log.retention.check.interval.ms", 1)],
    ),
}
_TIME_ITEMS = ("retention_ms", "roll_ms", "retention_check_interval_ms")
_UNLIMITED_ITEMS = ("retention_ms", "retention_bytes")


def static_keys_regex() -> str:
    """生成 grep -E 用的静态白名单键正则（供脚本使用）"""
    return "|".join(re.escape(key) for key in STATIC_WHITELIST)


def split_sections(raw_output: str) -> Dict[str, str]:
    """按 ===NAME=== 分隔符拆分脚本输出，没出现的段为空字符串"""
    sections = {name: "" for name in SECTIONS}
    current = ""
    for line in raw_output.splitlines():
        stripped = line.strip()
        matched = re.match(r"^===([A-Z_]+)===$", stripped)
        if matched and matched.group(1) in sections:
            current = matched.group(1)
        elif current:
            sections[current] += line + "\n"
    return sections


def has_end_marker(raw_output: str) -> bool:
    """脚本是否输出了独立成行的结束标记（不能用子串判断，topic 名等内容里可能含 END）"""
    return any(line.strip() == f"==={SECTION_END}===" for line in raw_output.splitlines())


def _lacks_default_broker_entity(major_version: str) -> bool:
    """1.1 以前没有"集群默认 broker 配置"这个实体，该查询静默无输出"""
    matched = re.match(r"^(\d+)\.(\d+)", major_version or "")
    return bool(matched) and (int(matched.group(1)), int(matched.group(2))) < (1, 1)


def parse_static_properties(text: str) -> Tuple[Dict[str, str], List[str]]:
    """
    解析 server.properties 白名单行。
    - 去掉空行、# 和 ! 开头的注释行
    - 键与值可用 = : 或空白分隔，两侧空白忽略
    - 同一个键出现多次取最后一次（Java Properties 的行为）
    - 值为空视为未配置并告警，不当成 0
    - 白名单外的键直接丢弃
    """
    configs: Dict[str, str] = {}
    warnings: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#!":
            continue
        matched = re.match(r"^([^\s=:]+)\s*[=:]?\s*(.*)$", line)
        if not matched:
            continue
        key, value = matched.group(1), matched.group(2).strip()
        if key not in STATIC_WHITELIST:
            continue
        if value == "":
            configs.pop(key, None)
            warnings.append(_("server.properties 中 {} 的值为空，按未配置处理").format(key))
            continue
        configs[key] = value
    return configs, warnings


_OVERRIDE_HEADER = re.compile(r"^(Dynamic configs for|Configs for|Default configs? for)\b")
_DYNAMIC_LINE = re.compile(r"^([^\s=]+)=(.*?)\s+sensitive=(?:true|false)\b")


def parse_overrides(text: str) -> Tuple[Dict[str, str], bool]:
    """
    解析 kafka-configs.sh --describe 的输出，返回 (配置项, 是否识别到有效输出)。
    兼容两种格式：
      1. ZK 模式：Configs for topic 'x' are a=b,c=d  /  Default config for brokers in the cluster are a=b
      2. bootstrap-server 模式：Dynamic configs for topic x are:\\n  a=b sensitive=false synonyms={...}
    "识别到有效输出"为 False 表示输出里没有任何已知的表头，通常是命令报错，调用方不能把它当成"没有覆盖项"。
    """
    configs: Dict[str, str] = {}
    recognized = False
    last_key: Optional[str] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _OVERRIDE_HEADER.match(line):
            recognized = True
            last_key = None
            if " are " not in line:
                continue
            config_part = line.split(" are ", 1)[1].strip()
            # 值里可能带逗号（如 cleanup.policy=delete,compact），没有 = 的片段接回上一个值
            for fragment in config_part.split(","):
                fragment = fragment.strip()
                if "=" in fragment:
                    key, value = fragment.split("=", 1)
                    last_key = key.strip()
                    configs[last_key] = value.strip()
                elif fragment and last_key:
                    configs[last_key] += "," + fragment
            continue
        matched = _DYNAMIC_LINE.match(line)
        if matched:
            recognized = True
            configs[matched.group(1)] = matched.group(2).strip()
    return configs, recognized


def _filter_layer(
    configs: Dict[str, str], allowed: Tuple[str, ...], invalid: Tuple[str, ...], layer_name: str
) -> Tuple[Dict[str, str], List[str]]:
    """只保留与有效值相关的键，并对该层不可能出现的键告警"""
    warnings = [_("{} 层出现了不支持的配置项 {}，已忽略").format(layer_name, key) for key in invalid if key in configs]
    # 空值与静态层一致，按未配置处理，否则会短路掉后面所有层
    for key in allowed:
        if key in configs and not configs[key].strip():
            warnings.append(_("{} 层的 {} 值为空，按未配置处理").format(layer_name, key))
    return {key: configs[key] for key in allowed if key in configs and configs[key].strip()}, warnings


def _to_int(value: str) -> Optional[int]:
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None


def _resolve_item(name: str, layers: Dict[str, Dict[str, str]]) -> Dict:
    kind, default, candidates = _EFFECTIVE_ITEMS[name]
    for layer, key, multiplier in candidates:
        if key not in layers.get(layer, {}):
            continue
        raw_value = layers[layer][key]
        if kind == KIND_STR:
            value, parse_error = raw_value.strip().lower(), False
        else:
            number = _to_int(raw_value)
            parse_error = number is None
            value = None if parse_error else number * multiplier
            # Kafka 对保留时间/大小的负数统一按 -1（不限制）处理
            if name in _UNLIMITED_ITEMS and value is not None and value < 0:
                value = -1
        # 命中的层取值非法时不继续往下找，否则会给出一个看似正确的错误结论
        return _item_result(name, value, layer, key, parse_error, raw_value)
    return _item_result(name, default, LAYER_DEFAULT, None, False, None)


def _item_result(
    name: str, value, source: str, key: Optional[str], parse_error: bool, raw_value: Optional[str]
) -> Dict:
    result = {"value": value, "source": source, "key": key}
    if parse_error:
        result["parse_error"] = True
        result["raw_value"] = raw_value
    if name in _TIME_ITEMS:
        result["hours"] = round(value / HOUR_MS, 2) if isinstance(value, int) and value >= 0 else None
    if name in _UNLIMITED_ITEMS:
        result["unlimited"] = isinstance(value, int) and value < 0
    return result


def compute_effective_config(
    topic_configs: Dict[str, str],
    broker_dynamic: Dict[str, str],
    broker_default_dynamic: Dict[str, str],
    broker_static: Dict[str, str],
) -> Dict[str, Dict]:
    """按优先级合并四层配置，返回每个有效值及其来源"""
    layers = {
        LAYER_TOPIC: topic_configs,
        LAYER_BROKER_DYNAMIC: broker_dynamic,
        LAYER_BROKER_DEFAULT_DYNAMIC: broker_default_dynamic,
        LAYER_BROKER_STATIC: broker_static,
    }
    return {name: _resolve_item(name, layers) for name in _EFFECTIVE_ITEMS}


def _version_warning(major_version: str) -> List[str]:
    matched = re.match(r"^(\d+)\.(\d+)", major_version or "")
    if not matched:
        return [_("无法识别集群版本 {}，默认值未核对").format(major_version)]
    if (int(matched.group(1)), int(matched.group(2))) > MAX_VERIFIED_VERSION:
        return [_("内置默认值只核对过 Kafka 2.4 及以下，当前版本 {} 的默认值未核对").format(major_version)]
    return []


def _section_warning(section_name: str, text: str) -> List[str]:
    # 有输出却没有任何已知表头，说明命令多半报错了，这时的"空"不代表没有覆盖项
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return [_("{} 查询没有得到可识别的输出，该层按无覆盖项处理，结果可能不完整：{}").format(section_name, first_line[:200])]


def build_effective_config_result(
    immute_domain: str, topic: str, broker_ip: str, major_version: str, raw_output: str
) -> Dict:
    """把脚本的原始输出整理成工具返回值"""
    sections = split_sections(raw_output)
    present_markers = {line.strip() for line in raw_output.splitlines()}
    warnings: List[str] = _version_warning(major_version)

    if not has_end_marker(raw_output):
        warnings.append(_("脚本输出不完整，缺少结束标记，结果可能不完整"))

    static_configs, static_warnings = parse_static_properties(sections[SECTION_STATIC])
    warnings.extend(static_warnings)
    if not static_configs:
        warnings.append(_("没有读到 server.properties 中的白名单配置项，静态值按未配置处理"))

    client_props_missing = sections[SECTION_CLIENT_PROPERTIES].strip() == CLIENT_PROPS_MISSING
    if client_props_missing:
        warnings.append(_("集群启用了 SASL，但 broker 上缺少 client.properties，无法取 broker.id 做认证访问，请补齐该文件（部署流程应生成）"))

    layer_inputs = [
        (SECTION_TOPIC, LAYER_TOPIC, TOPIC_KEYS, TOPIC_INVALID_KEYS),
        (SECTION_BROKER_DYNAMIC, LAYER_BROKER_DYNAMIC, DYNAMIC_KEYS, DYNAMIC_INVALID_KEYS),
        (SECTION_BROKER_DEFAULT_DYNAMIC, LAYER_BROKER_DEFAULT_DYNAMIC, DYNAMIC_KEYS, DYNAMIC_INVALID_KEYS),
    ]
    layers: Dict[str, Dict[str, str]] = {}
    for section_name, layer_name, allowed, invalid in layer_inputs:
        text = sections[section_name]
        if text.strip() == SKIPPED_MARK:
            if not client_props_missing:
                warnings.append(_("没有取到本机 broker.id（可能 broker 广播地址不是 IP），未查询 broker 动态配置"))
            layers[layer_name] = {}
            continue
        # 仅 1.1 以前的版本没有"集群默认 broker 配置"这个实体，命令静默无输出；其他版本空输出要告警
        if (
            section_name == SECTION_BROKER_DEFAULT_DYNAMIC
            and not text.strip()
            and f"==={section_name}===" in present_markers
            and _lacks_default_broker_entity(major_version)
        ):
            layers[layer_name] = {}
            continue
        # bootstrap-server 模式下 topic 不存在时的提示（ZK 模式下不会有）
        if section_name == SECTION_TOPIC and "doesn't exist" in text:
            warnings.append(_("topic {} 在该集群上不存在，topic 级覆盖项为空").format(topic))
            layers[layer_name] = {}
            continue
        parsed, recognized = parse_overrides(text)
        if not recognized:
            warnings.extend(_section_warning(layer_name, text))
        layers[layer_name], layer_warnings = _filter_layer(parsed, allowed, invalid, layer_name)
        warnings.extend(layer_warnings)

    static_relevant = {key: value for key, value in static_configs.items() if key != "broker.id"}
    effective = compute_effective_config(
        layers[LAYER_TOPIC],
        layers[LAYER_BROKER_DYNAMIC],
        layers[LAYER_BROKER_DEFAULT_DYNAMIC],
        static_relevant,
    )
    for name, item in effective.items():
        if item.get("parse_error"):
            warnings.append(
                _("{} 取自 {} 的 {}，值 {} 不是合法数字，有效值未知").format(name, item["source"], item["key"], item["raw_value"])
            )

    layers[LAYER_BROKER_STATIC] = static_relevant
    broker_id = sections[SECTION_BROKER_ID].strip() or static_configs.get("broker.id")
    return {
        "cluster_domain": immute_domain,
        "topic": topic,
        "broker_ip": broker_ip,
        "broker_id": broker_id if broker_id and broker_id.isdigit() else None,
        "effective": effective,
        "layers": layers,
        "warnings": [str(w) for w in warnings],
    }
