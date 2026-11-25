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

import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from backend.db_meta.enums import InstanceRole
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.hdfs.constants import ACTIVE_NN_STATE_ALIAS, HDFS_METRIC_REGISTRY, MIN_STEP_SECONDS
from backend.dbm_aiagent.mcp_tools.hdfs.enums import METRIC_ALL_ROLES, HdfsMetricName, get_hdfs_role_choices
from backend.dbm_aiagent.mcp_tools.hdfs.impl import hdfs_metrics as mod
from backend.dbm_aiagent.mcp_tools.hdfs.serializers.hdfs_metrics import HdfsMetricsInputSerializer

# 用例不访问 ORM：监控查询一律 mock，集群校验在视图层，不经过 impl。
# USE_TZ=True 时 DRF DateTimeField 解析出的是带时区时间，这里直接构造带时区时间模拟真实入参。
SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = datetime.timezone.utc


def _aware_now(tz=SHANGHAI) -> datetime.datetime:
    return timezone.now().astimezone(tz).replace(microsecond=0)


class TestToNaiveLocal:
    def test_none_and_naive_pass_through(self):
        naive = datetime.datetime(2026, 11, 10, 10, 0, 0)
        assert mod.to_naive_local(None) is None
        assert mod.to_naive_local(naive) is naive

    def test_aware_keeps_timestamp_and_drops_tzinfo(self):
        aware = datetime.datetime(2026, 11, 10, 10, 0, 0, tzinfo=SHANGHAI)
        result = mod.to_naive_local(aware)
        assert result.tzinfo is None
        assert result.timestamp() == aware.timestamp()

    def test_utc_input_is_converted_not_just_stripped(self):
        # 直接 replace(tzinfo=None) 会差 8 小时，这里锁住「先换算再去时区」
        aware_utc = datetime.datetime(2026, 11, 10, 2, 0, 0, tzinfo=UTC)
        result = mod.to_naive_local(aware_utc)
        assert result.tzinfo is None
        assert result.timestamp() == aware_utc.timestamp()


class TestValidateTimeRangeWithAwareInput:
    """转换后再校验，不应因 aware/naive 混算抛 TypeError。"""

    def test_aware_range_after_conversion(self):
        end = _aware_now()
        start = end - datetime.timedelta(hours=1)
        mod.validate_time_range(mod.to_naive_local(start), mod.to_naive_local(end), "1m")

    def test_aware_future_end_still_rejected(self):
        future = _aware_now() + datetime.timedelta(hours=1)
        with pytest.raises(DBMMcpBaseException):
            mod.validate_time_range(None, mod.to_naive_local(future), "1m")


@patch.object(mod, "query_promql_metrics_with_roles", return_value={"series": [], "promql": {}})
class TestQueryHdfsMetricsWithAwareInput:
    METRIC = HdfsMetricName.CPU_USAGE.value

    def _query(self, start_time=None, end_time=None):
        return mod.query_hdfs_metrics(
            cluster_domain="hdfs.test.db",
            metric_name=self.METRIC,
            start_time=start_time,
            end_time=end_time,
        )

    def _passed_builder(self, mock_query):
        return mock_query.call_args[0][2]

    def test_only_start_time(self, mock_query):
        start = _aware_now() - datetime.timedelta(hours=1)
        self._query(start_time=start)
        builder = self._passed_builder(mock_query)
        assert builder.start_time.tzinfo is None
        assert builder.start_time.timestamp() == start.timestamp()

    def test_only_end_time(self, mock_query):
        end = _aware_now()
        self._query(end_time=end)
        builder = self._passed_builder(mock_query)
        assert builder.end_time.tzinfo is None
        assert builder.end_time.timestamp() == end.timestamp()

    def test_both_times_in_utc(self, mock_query):
        end = _aware_now(UTC)
        start = end - datetime.timedelta(hours=2)
        self._query(start_time=start, end_time=end)
        builder = self._passed_builder(mock_query)
        assert builder.start_time.timestamp() == start.timestamp()
        assert builder.end_time.timestamp() == end.timestamp()

    def test_aware_start_after_end_rejected(self, mock_query):
        end = _aware_now() - datetime.timedelta(hours=1)
        with pytest.raises(DBMMcpBaseException):
            self._query(start_time=end + datetime.timedelta(minutes=30), end_time=end)
        mock_query.assert_not_called()


class TestValidateTimeRangeStepFormat:
    """P2 回归：非法 step 格式必须转可读业务异常，而不是裸 ValueError 被打成 500。"""

    def _range(self, hours=1):
        end = _aware_now()
        return mod.to_naive_local(end - datetime.timedelta(hours=hours)), mod.to_naive_local(end)

    # 边界值由 MIN_STEP_SECONDS 推导，避免在用例中重复写裸值
    @pytest.mark.parametrize("step", ["1w", "abc", "1h30m", "", "5"])
    def test_invalid_step_format_raises_readable_error(self, step):
        start, end = self._range()
        with pytest.raises(DBMMcpBaseException):
            mod.validate_time_range(start, end, step)

    def test_zero_step_rejected_before_division(self):
        start, end = self._range()
        with pytest.raises(DBMMcpBaseException):
            mod.validate_time_range(start, end, "0s")

    @pytest.mark.parametrize("step", [f"{MIN_STEP_SECONDS // 60}m", "5m", f"{MIN_STEP_SECONDS + 30}s", "1h", "1d"])
    def test_valid_steps_pass(self, step):
        start, end = self._range(hours=2)
        mod.validate_time_range(start, end, step)


class TestStepSerializerValidation:
    """入口层（序列化器）应先于 impl 拦截非法 step，返回 400 而不是 500。"""

    def _validated_step(self, step):
        slz = HdfsMetricsInputSerializer(
            data={"cluster_domain": "hdfs.test.db", "metric_name": HdfsMetricName.CPU_USAGE.value, "step": step}
        )
        assert slz.is_valid(), slz.errors
        return slz.validated_data["step"]

    def test_valid_steps_accepted(self):
        min_step = f"{MIN_STEP_SECONDS // 60}m"
        assert self._validated_step(min_step) == min_step

    @pytest.mark.parametrize("step", ["1w", "abc", "0s", f"{MIN_STEP_SECONDS - 1}s"])
    def test_invalid_steps_rejected_at_entry(self, step):
        slz = HdfsMetricsInputSerializer(
            data={"cluster_domain": "hdfs.test.db", "metric_name": HdfsMetricName.CPU_USAGE.value, "step": step}
        )
        assert not slz.is_valid()
        assert "step" in slz.errors


# State 相关查询必须保持瞬时值，其余指标统一取窗口峰值
_STATE_METRIC = HdfsMetricName.NAMENODE_STATE.value
_PEAK_METRICS = sorted(name for name in HDFS_METRIC_REGISTRY if name != _STATE_METRIC)


def _build_promql(metric_name: str, step: str) -> dict:
    spec = HDFS_METRIC_REGISTRY[metric_name]
    builder = mod._build_query_builder(
        spec=spec,
        aggregation=spec.default_aggregation,
        start_time=None,
        end_time=None,
        step=step,
    )
    promql = builder.prepare_promql()
    promql.pop("expression", None)
    return promql


class TestRangeFunctionPeak:
    """P2-2：摘要用 1h 步长时取每小时峰值，而不是每小时抽一个瞬时样本。"""

    @pytest.mark.parametrize("metric_name", _PEAK_METRICS)
    def test_business_queries_use_max_over_time_following_step(self, metric_name):
        promql = _build_promql(metric_name, "1h")
        business = {alias: q for alias, q in promql.items() if alias != ACTIVE_NN_STATE_ALIAS}
        assert business
        for query in business.values():
            assert "max_over_time(" in query
            assert query.endswith("[1h]))")

    @pytest.mark.parametrize("metric_name", _PEAK_METRICS)
    def test_default_step_window_is_1m(self, metric_name):
        promql = _build_promql(metric_name, "1m")
        for alias, query in promql.items():
            if alias != ACTIVE_NN_STATE_ALIAS:
                assert "[1m]" in query

    def test_disk_usage_uses_max_not_avg(self):
        (query,) = _build_promql(HdfsMetricName.DISK_USAGE.value, "1h").values()
        assert "avg_over_time" not in query
        assert "max_over_time(" in query

    def test_active_namenode_state_subquery_stays_instant(self):
        promql = _build_promql(HdfsMetricName.CAPACITY_USAGE.value, "1h")
        assert "_over_time" not in promql[ACTIVE_NN_STATE_ALIAS]
        assert "[" not in promql[ACTIVE_NN_STATE_ALIAS]

    def test_namenode_state_metric_stays_instant(self):
        (query,) = _build_promql(_STATE_METRIC, "1h").values()
        assert "_over_time" not in query
        assert "[" not in query


def test_performance_summary_has_no_overall_health():
    metric_name = HdfsMetricName.CPU_USAGE.value
    query_result = {"series": [{"datapoints": [[10, 1]]}]}
    with patch.object(mod, "SUMMARY_KEY_METRICS", (metric_name,)), patch.object(
        mod, "query_hdfs_metrics", return_value=query_result
    ):
        result = mod.get_hdfs_performance_summary("hdfs.test.db", days=1)

    assert "overall_health" not in result
    assert result["groups"]["resource"]["metrics"][metric_name]["health"] == "normal"


class TestMetricRoles:
    def test_role_choices_match_whitelist_and_exclude_jn_zk(self):
        values = {value for value, _label in get_hdfs_role_choices()}
        assert values == set(METRIC_ALL_ROLES)
        assert InstanceRole.HDFS_JOURNAL_NODE.value not in values
        assert InstanceRole.HDFS_ZOOKEEPER.value not in values
