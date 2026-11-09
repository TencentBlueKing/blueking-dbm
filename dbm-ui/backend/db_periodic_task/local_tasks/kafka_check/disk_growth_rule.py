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
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from backend.db_report.enums.kafka_disk_growth_sub_type import KafkaDiskGrowthRule

# 持续创新高：当天峰值不低于该值，且最近 CONTINUOUS_LOOKBACK_DAYS 天里至少 CONTINUOUS_MIN_DAYS 天的日峰值
# 比各自此前 HISTORY_WINDOW_DAYS 天的最高值高出 CONTINUOUS_MARGIN 个点以上
CONTINUOUS_PEAK_FLOOR = 60.0
CONTINUOUS_MARGIN = 2.0
CONTINUOUS_LOOKBACK_DAYS = 3
CONTINUOUS_MIN_DAYS = 2

# 单日跳涨：当天峰值不低于该值，且比此前 HISTORY_WINDOW_DAYS 天的最高值高出 JUMP_MARGIN 个点以上
JUMP_PEAK_FLOOR = 50.0
JUMP_MARGIN = 15.0

# 7天窗口必然包含上一个完整的周末，周末峰值只有高过上周末才算创新高，不需要单独识别周末效应
HISTORY_WINDOW_DAYS = 7
# 报告里展示的日峰值天数（含判定当天）
SERIES_DAYS = 8
# 日均涨幅按最近几天计算
GROWTH_AVG_DAYS = 3
# 判定一天需要的最早数据：判定日往前 (CONTINUOUS_LOOKBACK_DAYS - 1) + HISTORY_WINDOW_DAYS 天
REQUIRED_HISTORY_DAYS = CONTINUOUS_LOOKBACK_DAYS - 1 + HISTORY_WINDOW_DAYS


@dataclass
class GrowthHit:
    rule: str
    peak: float
    # 判定当天峰值比此前7天最高值高出的点数
    excess: float
    # 最近几天平均每天涨几个点
    daily_growth: float
    # 最近 SERIES_DAYS 天的日峰值，按日期升序
    peaks: List[Dict]


def _excess_over_history(peaks: Dict[date, float], day: date) -> Optional[float]:
    """day 的峰值比此前 HISTORY_WINDOW_DAYS 天最高值高出多少；当天或此前任何一天缺数据则返回 None"""
    current = peaks.get(day)
    if current is None:
        return None
    history = [peaks.get(day - timedelta(days=offset)) for offset in range(1, HISTORY_WINDOW_DAYS + 1)]
    if any(value is None for value in history):
        return None
    return current - max(history)


def evaluate(peaks: Dict[date, float], day: date) -> Optional[GrowthHit]:
    """
    判断某个 broker 挂载点在 day 这一天是否命中“磁盘持续增长”规则。

    :param peaks: 日期 -> 当天磁盘使用率峰值（%）。午后巡检时 day 当天的值是截至当时的峰值
    :param day: 判定日期
    :return: 命中返回 GrowthHit，否则返回 None。两条规则都满足时记为持续创新高
    """
    excess = _excess_over_history(peaks, day)
    if excess is None:
        # 判定当天或此前7天缺数据，数据不完整时不判定，避免用残缺的窗口得出错误结论
        return None
    current = peaks[day]

    new_high_days = 0
    for offset in range(CONTINUOUS_LOOKBACK_DAYS):
        day_excess = excess if offset == 0 else _excess_over_history(peaks, day - timedelta(days=offset))
        # 较早的几天缺数据时只是不计入创新高天数，不影响整次判定
        if day_excess is not None and day_excess >= CONTINUOUS_MARGIN:
            new_high_days += 1

    if current >= CONTINUOUS_PEAK_FLOOR and new_high_days >= CONTINUOUS_MIN_DAYS:
        rule = KafkaDiskGrowthRule.CONTINUOUS_NEW_HIGH.value
    elif current >= JUMP_PEAK_FLOOR and excess >= JUMP_MARGIN:
        rule = KafkaDiskGrowthRule.SINGLE_DAY_JUMP.value
    else:
        return None

    base = peaks.get(day - timedelta(days=GROWTH_AVG_DAYS))
    daily_growth = (current - base) / GROWTH_AVG_DAYS if base is not None else 0.0
    series = [
        {"day": (day - timedelta(days=offset)).isoformat(), "peak": round(peaks[day - timedelta(days=offset)], 1)}
        for offset in range(SERIES_DAYS - 1, -1, -1)
        if (day - timedelta(days=offset)) in peaks
    ]
    return GrowthHit(
        rule=rule,
        peak=round(current, 1),
        excess=round(excess, 1),
        daily_growth=round(daily_growth, 1),
        peaks=series,
    )
