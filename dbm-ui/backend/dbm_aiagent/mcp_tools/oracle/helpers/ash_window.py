# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

ASH 窗口判定的公共逻辑，由内存 ASH（impl/performance.py）与历史 ASH（impl/ash_history.py）共用。

两个数据源的阈值与判定口径必须完全一致，否则「实时说 high、历史说 normal」会让结论无法衔接，
因此判定全部集中在本模块，调用方只负责拼装各自的窗口字段与提示文案。

关键差异由参数传入：
- sample_interval_sec：内存 ASH 1 秒 / 历史 ASH 10 秒，只用于把样本数换算成 DB time 与 AAS；
- 样本是否足以支撑占比结论（sample_sufficient）一律按原始样本数判定，不乘该倍率。
"""

from typing import Any, Dict, Optional

from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_ASH_MIN_COVERAGE_PCT

# 实际窗口比请求窗口短超过该秒数时，视为被截断
TRUNCATE_TOLERANCE_SEC = 60

# 请求终点超出数据可用终点该秒数以上时给出提示
FUTURE_TOLERANCE_SEC = 60

# CPU 繁忙度阈值：AAS(CPU) / cpu_count
_AAS_PER_CPU_LOW = 0.5
_AAS_PER_CPU_NORMAL = 0.8
_AAS_PER_CPU_HIGH = 1.2

# 等待 AAS 达到该值且不低于 CPU AAS 时，提示瓶颈不在 CPU
_WAIT_HINT_MIN_AAS = 1.0

# 活跃度阈值（基于 total_aas，经验值）
_IDLE_TOTAL_AAS = 0.1
_IDLE_PEAK_AAS = 1.0
_LIGHT_TOTAL_AAS = 1.0

# 突发判定：峰值桶 AAS 不低于绝对值且为平均值的若干倍
_BURST_MIN_AAS = 1.0
_BURST_RATIO = 3.0

# 样本数低于该值时，占比（pct）不具统计意义
MIN_SAMPLES_FOR_PCT = 60

# 精简 window 字段，load / activity 仅由 wait_class 工具返回
_SLIM_WINDOW_KEYS = (
    "actual_begin",
    "actual_end",
    "effective_sec",
    "coverage_pct",
    "coverage_sufficient",
    "truncated",
    "total_db_time_sec",
    "warnings",
)


def to_db_time_sec(samples: Any, sample_interval_sec: int) -> int:
    """样本数 -> DB time 秒数。"""
    return int(samples or 0) * sample_interval_sec


def compute_aas(db_time_sec: Any, effective_sec: int) -> Optional[float]:
    """DB time 秒数 -> AAS（平均活跃会话数）；窗口为空时返回 None。"""
    if not effective_sec or effective_sec <= 0:
        return None
    return round((db_time_sec or 0) / effective_sec, 2)


def compute_coverage(requested_sec: int, effective_sec: int) -> Dict[str, Any]:
    """实际覆盖率；coverage_sufficient=false 表示数据源覆盖不足，应换数据源。"""
    coverage_pct = round(effective_sec * 100 / requested_sec, 1) if requested_sec > 0 else 0.0
    return {
        "coverage_pct": coverage_pct,
        "min_coverage_pct": ORACLE_ASH_MIN_COVERAGE_PCT,
        "coverage_sufficient": coverage_pct >= ORACLE_ASH_MIN_COVERAGE_PCT,
        "truncated": effective_sec < requested_sec - TRUNCATE_TOLERANCE_SEC,
    }


def derive_load(
    total_aas: Optional[float],
    cpu_aas: Optional[float],
    cpu_count: Any,
) -> Dict[str, Any]:
    """用 AAS(ON CPU) / cpu_count 判定 CPU 繁忙度；等待占主导时在 summary 中提示。"""
    wait_aas = None
    if total_aas is not None and cpu_aas is not None:
        wait_aas = round(total_aas - cpu_aas, 2)

    if cpu_aas is None or not cpu_count:
        return {
            "cpu_count": cpu_count,
            "aas_cpu": cpu_aas,
            "aas_wait": wait_aas,
            "aas_cpu_per_core": None,
            "wait_dominant": None,
            "level": "unknown",
            "summary": "cpu_count 或 ASH 样本不可用，无法判定 CPU 繁忙度",
        }

    cpu_count = int(cpu_count)
    aas_cpu_per_core = round(cpu_aas / cpu_count, 2)
    if aas_cpu_per_core < _AAS_PER_CPU_LOW:
        level, summary = "low", "CPU 仍有明显余量"
    elif aas_cpu_per_core < _AAS_PER_CPU_NORMAL:
        level, summary = "normal", "ON CPU 会话数接近 CPU 核数，繁忙但基本能被 CPU 消化"
    elif aas_cpu_per_core < _AAS_PER_CPU_HIGH:
        level, summary = "high", "ON CPU 会话数超过 CPU 核数，CPU 上存在排队"
    else:
        level, summary = "critical", "ON CPU 会话数远超 CPU 核数，CPU 已过载"
    summary = f"{summary}（aas_cpu={cpu_aas} / cpu_count={cpu_count} = {aas_cpu_per_core}）"

    wait_dominant = bool(wait_aas is not None and wait_aas >= cpu_aas and wait_aas >= _WAIT_HINT_MIN_AAS)
    if wait_dominant:
        summary += f"；但整体 total_aas={total_aas} 中有 {wait_aas} 来自等待而非 CPU，瓶颈不在 CPU"

    return {
        "cpu_count": cpu_count,
        "aas_cpu": cpu_aas,
        "aas_wait": wait_aas,
        "aas_cpu_per_core": aas_cpu_per_core,
        "wait_dominant": wait_dominant,
        "level": level,
        "summary": summary,
    }


def derive_activity(
    total_aas: Optional[float],
    total_samples: int,
    peak_samples: Any,
    peak_label: Optional[str],
    actual_begin: Optional[str],
    actual_end: Optional[str],
    sample_interval_sec: int = 1,
    peak_bucket_sec: int = 60,
    peak_field: str = "peak_minute",
) -> Dict[str, Any]:
    """判定窗口内数据库活跃度：idle / light / active，并识别被平均值掩盖的突发。

    peak_samples / peak_bucket_sec 描述「最忙的一个时间桶」，内存 ASH 用 1 分钟桶，
    历史 ASH 因 10 秒一个样本，1 分钟桶最多只有 6 个样本，由调用方改用更宽的桶并相应传入桶长。
    sample_sufficient 用原始 total_samples 判定，不受 sample_interval_sec 影响。
    """
    sample_sufficient = total_samples >= MIN_SAMPLES_FOR_PCT
    peak_db_time = to_db_time_sec(peak_samples, sample_interval_sec)
    peak_aas = round(peak_db_time / peak_bucket_sec, 2) if peak_samples else 0.0
    base = {
        peak_field: peak_label,
        f"{peak_field}_aas": peak_aas,
        "peak_bucket_sec": peak_bucket_sec,
        "sample_sufficient": sample_sufficient,
        "min_samples_for_pct": MIN_SAMPLES_FOR_PCT,
    }

    if total_aas is None:
        return {
            **base,
            "level": "unknown",
            "bursty": None,
            "summary": "ASH 在该窗口内没有任何可用样本，无法判定数据库活跃度",
        }

    bursty = peak_aas >= _BURST_MIN_AAS and peak_aas >= _BURST_RATIO * total_aas

    if total_aas < _IDLE_TOTAL_AAS and peak_aas < _IDLE_PEAK_AAS:
        level, summary = "idle", "数据库基本空闲，系统级不存在资源争用"
    elif total_aas < _LIGHT_TOTAL_AAS:
        level, summary = "light", "有负载但较轻，不构成系统级资源争用"
    else:
        level, summary = "active", "数据库有实际负载"
    summary = f"[{actual_begin} ~ {actual_end}] {summary}（total_aas={total_aas}，峰值桶 AAS={peak_aas}）"

    if bursty:
        ratio = round(peak_aas / total_aas, 1) if total_aas > 0 else None
        summary += f"；负载集中在 {peak_label}（该时段 AAS={peak_aas}，约为窗口平均的 {ratio} 倍），平均值掩盖了突发"
    if not sample_sufficient:
        summary += f"；样本仅 {total_samples} 个（< {MIN_SAMPLES_FOR_PCT}），wait class / 事件 / SQL 的占比不具统计意义"

    return {**base, "level": level, "bursty": bursty, "summary": summary}


def slim_window(window: Dict[str, Any]) -> Dict[str, Any]:
    """裁剪出精简 window：只保留描述本次统计区间与可信度的字段。"""
    slim: Dict[str, Any] = {key: window.get(key) for key in _SLIM_WINDOW_KEYS}
    slim["sample_sufficient"] = window.get("activity", {}).get("sample_sufficient")
    return slim
