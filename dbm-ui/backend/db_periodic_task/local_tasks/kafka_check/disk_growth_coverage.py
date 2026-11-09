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
import math
from dataclasses import dataclass
from typing import Dict, Tuple

# 以下是首版的工程默认值，不是根据现网数据推导出来的，等日志里积累了缺失分布再调整
# 一天里有效小时点占“应有小时数”的最低比例（百分比，用整数运算避免浮点误差）
MIN_COVERAGE_PERCENT = 80
# 允许连续缺失的最长小时数，超过说明缺口可能正好盖住了业务高峰
MAX_MISSING_RUN = 2

HOURS_PER_DAY = 24

REASON_INSUFFICIENT_POINTS = "insufficient_points"
REASON_LONG_GAP = "long_gap"
REASON_LAST_HOUR_MISSING = "last_hour_missing"


@dataclass(frozen=True)
class DayCoverage:
    ok: bool
    valid: int
    expected: int
    longest_gap: int
    reasons: Tuple[str, ...]


def is_valid_value(value) -> bool:
    """None、NaN、Inf 都不算有效点"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def required_points(expected: int) -> int:
    """ceil(expected * MIN_COVERAGE_PERCENT / 100)，用整数运算"""
    return -(-expected * MIN_COVERAGE_PERCENT // 100)


def _longest_missing_run(hours: Dict[int, float], expected: int) -> int:
    longest = current = 0
    for hour in range(expected):
        if hour in hours:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def assess_day(hours: Dict[int, float], expected: int, require_last: bool) -> DayCoverage:
    """
    判断一天的小时点是否足够可信地算日峰值。
    hours: {小时序号: 峰值}，序号 h 表示 [h:00, h+1:00) 这个小时窗口，已按小时去重
    expected: 已结束的小时窗口数（历史完整日是 24，午后当天是已走完的小时数）
    require_last: 最后一个已结束的小时窗口必须有数据（只用于未走完的当天）
    只统计序号小于 expected 的点；还没走完的小时窗口不参与覆盖率，有数据也可以用来求峰值
    """
    if expected <= 0:
        return DayCoverage(False, 0, 0, 0, (REASON_INSUFFICIENT_POINTS,))

    valid = sum(1 for hour in range(expected) if hour in hours)
    longest_gap = _longest_missing_run(hours, expected)
    reasons = []
    if valid < required_points(expected):
        reasons.append(REASON_INSUFFICIENT_POINTS)
    if longest_gap > MAX_MISSING_RUN:
        reasons.append(REASON_LONG_GAP)
    if require_last and (expected - 1) not in hours:
        reasons.append(REASON_LAST_HOUR_MISSING)
    return DayCoverage(not reasons, valid, expected, longest_gap, tuple(reasons))
