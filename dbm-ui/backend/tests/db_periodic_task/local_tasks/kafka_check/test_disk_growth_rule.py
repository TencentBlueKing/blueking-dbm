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
from datetime import date, timedelta

import pytest

DAY = date(2026, 11, 5)


def make_peaks(values, day=DAY):
    """values 按时间从旧到新排列，最后一个是 day 当天"""
    return {day - timedelta(days=len(values) - 1 - index): value for index, value in enumerate(values)}


class TestEvaluateHit:
    def test_continuous_new_high(self, rule_mod):
        hit = rule_mod.evaluate(make_peaks([50, 50, 50, 50, 50, 50, 50, 55, 58, 62]), DAY)
        assert hit.rule == "continuous_new_high"
        assert hit.peak == 62
        # 62 比此前7天最高的 58 高 4 个点
        assert hit.excess == 4.0
        # 近3天日均涨幅：(62 - 3天前的 50) / 3
        assert hit.daily_growth == 4.0

    def test_series_is_ascending_and_rounded(self, rule_mod):
        hit = rule_mod.evaluate(make_peaks([50, 50, 50, 50, 50, 50, 50.04, 55, 58, 62.26]), DAY)
        assert len(hit.peaks) == rule_mod.SERIES_DAYS
        assert [point["day"] for point in hit.peaks] == sorted(point["day"] for point in hit.peaks)
        assert hit.peaks[0] == {"day": "2026-10-29", "peak": 50.0}
        assert hit.peaks[-1] == {"day": "2026-11-05", "peak": 62.3}

    def test_single_day_jump(self, rule_mod):
        # 此前一直平稳，当天突然涨 16 个点，峰值不到 60，只会命中单日跳涨
        hit = rule_mod.evaluate(make_peaks([40] * 9 + [56]), DAY)
        assert hit.rule == "single_day_jump"
        assert hit.excess == 16.0

    def test_both_rules_prefer_continuous(self, rule_mod):
        peaks = make_peaks([40] * 8 + [50, 70])
        assert rule_mod.evaluate(peaks, DAY).rule == "continuous_new_high"

    @pytest.mark.parametrize("jump, expect_hit", [(15.0, True), (14.9, False)])
    def test_jump_margin_boundary(self, rule_mod, jump, expect_hit):
        # 峰值 55 低于持续创新高的 60 门槛，只看单日跳涨的 15 个点边界
        peaks = make_peaks([40.0] * 9 + [40 + jump])
        assert (rule_mod.evaluate(peaks, DAY) is not None) is expect_hit

    @pytest.mark.parametrize("step, expect_hit", [(2.0, True), (1.9, False)])
    def test_continuous_margin_boundary(self, rule_mod, step, expect_hit):
        # 此前平稳在 60，最近两天每天比此前最高值高 step 个点
        peaks = make_peaks([60.0] * 8 + [60.0 + step, 60.0 + 2 * step])
        assert (rule_mod.evaluate(peaks, DAY) is not None) is expect_hit


class TestEvaluateMiss:
    def test_weekend_peak_not_exceeded(self, rule_mod):
        # 7天前的周末峰值是 70，近几天虽然在涨且超过 60，但没有超过上个周末，不算增长
        peaks = make_peaks([60, 60, 70, 62, 60, 60, 61, 62, 66, 68])
        assert rule_mod.evaluate(peaks, DAY) is None

    def test_low_water_not_reported(self, rule_mod):
        # 连续创新高，但峰值 55 低于 60；涨幅也不到 15 个点
        peaks = make_peaks([40, 41, 42, 43, 44, 45, 46, 50, 53, 55])
        assert rule_mod.evaluate(peaks, DAY) is None

    def test_flat_high_water_not_reported(self, rule_mod):
        # 长期贴在高水位但没有增长，不属于本规则
        assert rule_mod.evaluate(make_peaks([89.0] * 10), DAY) is None

    def test_missing_history_day_not_evaluated(self, rule_mod):
        peaks = make_peaks([50, 50, 50, 50, 50, 50, 50, 55, 58, 62])
        del peaks[DAY - timedelta(days=4)]
        assert rule_mod.evaluate(peaks, DAY) is None

    def test_missing_today_not_evaluated(self, rule_mod):
        peaks = make_peaks([50, 50, 50, 50, 50, 50, 50, 55, 58, 62])
        del peaks[DAY]
        assert rule_mod.evaluate(peaks, DAY) is None

    def test_empty(self, rule_mod):
        assert rule_mod.evaluate({}, DAY) is None


class TestEvaluateEarlierDayMissing:
    def test_missing_oldest_day_only_skips_that_day(self, rule_mod):
        # 缺的是最早的一天：它只影响 day-2 的“此前7天”，当天和前一天仍然可以判定
        peaks = make_peaks([50, 50, 50, 50, 50, 50, 50, 55, 58, 62])
        del peaks[DAY - timedelta(days=9)]
        hit = rule_mod.evaluate(peaks, DAY)
        assert hit is not None
        assert hit.rule == "continuous_new_high"

    def test_missing_oldest_day_not_enough_new_highs(self, rule_mod):
        # 同样缺最早一天，但只有当天一天创新高，不满足“3天里至少2天”
        peaks = make_peaks([60, 60, 60, 60, 60, 60, 60, 60, 60, 63])
        del peaks[DAY - timedelta(days=9)]
        assert rule_mod.evaluate(peaks, DAY) is None
