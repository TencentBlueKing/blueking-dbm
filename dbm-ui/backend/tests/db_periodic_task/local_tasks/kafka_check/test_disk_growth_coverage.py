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
import pytest


def hours(*missing, total=24):
    return {hour: 50.0 for hour in range(total) if hour not in missing}


class TestRequiredPoints:
    @pytest.mark.parametrize("expected, need", [(24, 20), (16, 13), (10, 8), (1, 1), (5, 4)])
    def test_ceil_of_80_percent(self, cov, expected, need):
        assert cov.required_points(expected) == need


class TestAssessDay:
    def test_full_day_ok(self, cov):
        assert cov.assess_day(hours(), 24, require_last=False).ok

    def test_exactly_20_points_ok(self, cov):
        assert cov.assess_day(hours(1, 5, 9, 13), 24, require_last=False).ok

    def test_19_points_not_ok(self, cov):
        result = cov.assess_day(hours(1, 5, 9, 13, 17), 24, require_last=False)
        assert not result.ok and result.reasons == (cov.REASON_INSUFFICIENT_POINTS,)

    def test_gap_of_2_ok_gap_of_3_not(self, cov):
        assert cov.assess_day(hours(10, 11), 24, require_last=False).ok
        result = cov.assess_day(hours(10, 11, 12), 24, require_last=False)
        assert not result.ok and result.longest_gap == 3 and result.reasons == (cov.REASON_LONG_GAP,)

    def test_16_finished_hours_need_13_and_last_hour(self, cov):
        data = hours(2, 7, 11, total=16)  # 13 个有效点，最后一个小时（15）存在
        assert cov.assess_day(data, 16, require_last=True).ok
        assert not cov.assess_day(hours(2, 7, 11, 12, total=16), 16, require_last=True).ok

    def test_last_hour_missing_only_matters_when_required(self, cov):
        data = hours(15, total=16)
        assert cov.assess_day(data, 16, require_last=False).ok
        result = cov.assess_day(data, 16, require_last=True)
        assert not result.ok and result.reasons == (cov.REASON_LAST_HOUR_MISSING,)

    def test_unfinished_hours_do_not_count_toward_coverage(self, cov):
        # 序号 16 的窗口还没走完：它有数据也不能凑覆盖数
        data = hours(2, 7, 11, 12, total=16)
        data[16] = 60.0
        assert not cov.assess_day(data, 16, require_last=True).ok

    def test_multiple_reasons_reported(self, cov):
        result = cov.assess_day(hours(*range(0, 10)), 24, require_last=False)
        assert set(result.reasons) == {cov.REASON_INSUFFICIENT_POINTS, cov.REASON_LONG_GAP}

    def test_nothing_finished_is_not_ok(self, cov):
        assert not cov.assess_day({}, 0, require_last=True).ok


class TestIsValidValue:
    @pytest.mark.parametrize("value", [0, 0.0, 50, 99.9])
    def test_valid(self, cov, value):
        assert cov.is_valid_value(value)

    @pytest.mark.parametrize("value", [None, float("nan"), float("inf"), float("-inf"), "50", True])
    def test_invalid(self, cov, value):
        assert not cov.is_valid_value(value)
