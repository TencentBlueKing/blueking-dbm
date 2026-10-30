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
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from promql_builder.builders import promql

from backend import env
from backend.components import BKMonitorV3Api
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("root")

# 查询模板
UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "A",
    # 单位：s
    "start_time": 0,
    "end_time": 0,
    "slimit": 500,
    "down_sample_range": "1m",
    "type": "range",
}

# step 字符串到秒数的映射
STEP_PATTERN = re.compile(r"^(\d+)(s|m|h|d)$")
STEP_UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}

# 最大查询时间范围限制：24 小时
MAX_QUERY_RANGE_SECONDS = 24 * 3600

# label 匹配操作符到 VectorExpr 方法名的映射
LABEL_OP_METHOD_MAP = {
    "equal": "label",
    "not_equal": "label_neq",
    "match": "label_match_regexp",
    "not_match": "label_not_match_regexp",
}

# 正则类操作符
REGEX_OP_NAMES = ("match", "not_match")

# PromQL 合法字符集/格式，用于校验用户输入，防止拼接到 PromQL 表达式时注入
# 指标名: [a-zA-Z_:][a-zA-Z0-9_:]*，标签名: [a-zA-Z_][a-zA-Z0-9_]*
LABEL_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
METRIC_NAME_PATTERN = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
DURATION_PATTERN = re.compile(r"^(\d+(ms|s|m|h|d|w|y))+$")


def validate_label_name(name: str) -> str:
    """校验标签名，标签名会直接拼入 PromQL 表达式（by(...) / {name=...}），只允许合法字符"""
    name = str(name)
    if not LABEL_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid label name: {name!r}")
    return name


def escape_label_value(value, is_regex: bool = False) -> str:
    """
    转义 label value，防止 value 中的引号逃逸出 PromQL 字符串字面量
    例如 value 为 `x"} or up{`，不转义时会拼出 `cluster_domain="x"} or up{"`，注入额外的查询
    """
    value = str(value)
    if is_regex:
        # 正则匹配只转义引号，保留 \d、.* 等用户正则语义
        return value.replace('"', '\\"')
    return value.replace("\\", "\\\\").replace('"', '\\"')


# 支持的外层聚合函数（promql_builder 中的函数）
AGGREGATION_FUNC_MAP = {
    "max": promql.max,
    "min": promql.min,
    "sum": promql.sum,
    "avg": promql.avg,
    "count": promql.count,
}

# 支持的 range function（promql_builder 中的函数）
RANGE_FUNC_MAP = {
    "max": promql.max_over_time,
    "min": promql.min_over_time,
    "sum": promql.sum_over_time,
    "avg": promql.avg_over_time,
    "rate": promql.rate,
    "irate": promql.irate,
    "increase": promql.increase,
    "count": promql.count_over_time,
}


@dataclass
class PromQLQueryBuilder:
    """PromQL 查询参数及构建器
    start_time,end_time,step 不参与 promql 的生成，而是直接传递给 unify_query 接口
    """

    metric_name: str
    alias: Optional[str] = None
    filters: Optional[List[Dict]] = field(default_factory=list)
    group_by: Optional[List[str]] = field(default_factory=list)
    aggregation: Optional[str] = None
    range_function: Optional[str] = None
    time_window: Optional[str] = None
    aggregation_outer: Optional[str] = None

    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    step: str = "1m"

    def _validate_query_params(self):
        """校验 alias / time_window / group_by 参数"""
        if not self.alias:
            self.alias = self.metric_name

        # time_window 会拼入 [time_window]，校验合法的 duration 格式
        if self.time_window and not DURATION_PATTERN.match(self.time_window):
            raise ValueError(f"Invalid time_window: {self.time_window!r}")

        # group_by 的标签会拼入 by(...)，校验合法的标签名
        if self.group_by:
            for label in self.group_by:
                validate_label_name(label)

    def _normalize_metric_name(self):
        """转换并校验 metric_name"""
        # 转换一下 metric_name
        if self.metric_name.startswith("mysql_"):
            self.metric_name = "bkmonitor:exporter_dbm_mysqld_exporter:__default__:" + self.metric_name
        elif not self.metric_name:
            raise ValueError("metric_name must be specified")
        elif not self.metric_name.startswith("bkmonitor:"):
            self.metric_name = "bkmonitor:dbm_system:" + self.metric_name

        # metric_name 会直接拼入 PromQL，校验合法字符集，防止注入
        if not METRIC_NAME_PATTERN.match(self.metric_name):
            raise ValueError(f"Invalid metric_name: {self.metric_name!r}")

    def _build_vector(self) -> "promql.VectorExpr":
        """使用 promql-builder 构建 VectorExpr（metric + label 过滤）"""
        vector = promql.VectorExpr().metric(self.metric_name)

        if self.filters:
            for f in self.filters:
                # 兼容序列化器字段名 label / label_name
                label_name = f.get("label_name") or f.get("label")
                op = f["op"]
                value = f["value"]

                method_name = LABEL_OP_METHOD_MAP.get(op)
                if method_name is None:
                    raise ValueError(
                        f"Unsupported label operator: {op}, supported: {list(LABEL_OP_METHOD_MAP.keys())}"
                    )

                # 标签名只允许合法字符，value 转义引号，防止逃逸出 label 匹配器注入额外 PromQL
                validate_label_name(label_name)
                vector = getattr(vector, method_name)(
                    label_name, escape_label_value(value, is_regex=op in REGEX_OP_NAMES)
                )

        return vector

    def _apply_range_function(self, vector: "promql.VectorExpr"):
        """应用 range function（如果指定）"""
        if not self.range_function:
            return vector

        range_func = RANGE_FUNC_MAP.get(self.range_function)
        if range_func is None:
            raise ValueError(
                f"Unsupported range_function: {self.range_function}, supported: {list(RANGE_FUNC_MAP.keys())}"
            )

        if not self.time_window:
            raise ValueError("time_window must be specified when using range_function")

        return range_func(vector.range(self.time_window))

    def _get_aggregation_func(self, aggregation: str):
        """获取外层聚合函数，不支持则抛错"""
        agg_func = AGGREGATION_FUNC_MAP.get(aggregation)
        if agg_func is None:
            raise ValueError(
                f"Unsupported aggregation function: {aggregation}, supported: {list(AGGREGATION_FUNC_MAP.keys())}"
            )
        return agg_func

    def _apply_aggregation_outer(self, agg_expr):
        """应用最外层聚合（aggregation_outer，格式如 sum:cluster_domain,instance_role）"""
        # sum:cluster_domain,instance_role
        agg_outer_type, agg_outer_labels = self.aggregation_outer.split(":")
        agg_func_outer = self._get_aggregation_func(agg_outer_type)
        agg_expr = agg_func_outer(agg_expr)
        if agg_outer_labels:
            agg_outer_labels_list = agg_outer_labels.split(",")
            for label in agg_outer_labels_list:
                validate_label_name(label)
            agg_expr = agg_expr.by(agg_outer_labels_list)
        return agg_expr

    def _apply_aggregation(self, expr) -> str:
        """应用外层聚合函数（如果指定），返回构建好的 PromQL 字符串"""
        if not self.aggregation:
            return str(expr.build())

        agg_func = self._get_aggregation_func(self.aggregation)
        agg_expr = agg_func(expr)
        if self.group_by:
            agg_expr = agg_expr.by(self.group_by)

        if self.aggregation_outer:
            agg_expr = self._apply_aggregation_outer(agg_expr)

        return str(agg_expr.build())

    def build_promql(self) -> Dict[str, str]:
        """
        使用 promql-builder 根据自身参数构建 PromQL 查询字符串

        @return: 构建好的 PromQL 字符串
        """
        # 校验并规范化参数
        self._validate_query_params()
        self._normalize_metric_name()

        # 1. 构建 VectorExpr（metric + label 过滤）
        vector = self._build_vector()

        # 2. 应用 range function（如果指定）
        expr = self._apply_range_function(vector)

        # 3. 应用外层聚合函数（如果指定）并构建 PromQL 字符串
        promql_str = self._apply_aggregation(expr)

        return {self.alias: promql_str}

    def prepare_promql(self) -> Dict[str, str]:
        """
        通用 PromQL 指标查询

        @return: promql string
        """
        # 1. 处理时间参数
        if self.end_time:
            end_ts = timezone2timestamp(self.end_time)
        else:
            end_ts = int(time.time())
            self.end_time = datetime.datetime.fromtimestamp(end_ts)

        if self.start_time:
            start_ts = timezone2timestamp(self.start_time)
        else:
            # 默认查询最近 5 分钟
            start_ts = end_ts - 5 * 60
            self.start_time = datetime.datetime.fromtimestamp(start_ts)

        if end_ts - start_ts > MAX_QUERY_RANGE_SECONDS:
            pass
            # raise ValueError(f"Query time range too large, maximum {MAX_QUERY_RANGE_SECONDS // 3600} hours")

        # 3. 如果未指定 time_window，默认使用 step
        if not self.time_window:
            self.time_window = self.step

        # 4. 构建 PromQL
        return self.build_promql()

    def get_aggregation(self) -> str:
        return self.aggregation


@dataclass
class PromQLMultiQueryBuilder(PromQLQueryBuilder):
    """多 PromQL 查询构建器，用于多个查询结果做表达式计算（如 used/total）

    queries: 子查询字典，key 是 alias（如 "a", "b"），value 是 PromQLQueryBuilder
    expression: 表达式，如 "(a / b) * 100"
    alias: 外层表达式的 alias，默认 "AA"
    """

    metric_name: str = ""  # PromQLMultiQueryBuilder 不需要 metric_name
    alias: str = "AA"
    queries: Dict[str, PromQLQueryBuilder] = field(default_factory=dict)
    expression: str = ""
    aggregation: Optional[str] = None

    def build_promql(self) -> Dict[str, str]:
        """
        构建多个子查询的 PromQL，返回 {alias: promql_str} 字典

        @return: 子查询 alias 到 PromQL 字符串的映射
        """
        if not self.queries:
            raise ValueError("queries must not be empty for PromQLMultiQueryBuilder")
        if not self.expression:
            raise ValueError("expression must be specified for PromQLMultiQueryBuilder")

        prom_queries = {}
        for alias, one_builder in self.queries.items():
            one_builder.time_window = self.time_window
            one_builder.filters.extend(self.filters)
            one_builder.alias = alias
            prom_queries.update(one_builder.build_promql())
        prom_queries.update({"expression": self.expression})
        return prom_queries

    def prepare_promql(self) -> Dict[str, str]:
        return super().prepare_promql()

    def get_aggregation(self) -> str:
        return list(self.queries.values())[0].aggregation


def parse_step_to_seconds(step: str) -> int:
    """将 step 字符串（如 '1m', '5m', '1h'）解析为秒数"""
    match = STEP_PATTERN.match(step)
    if not match:
        raise ValueError(f"Invalid step format: {step}, expected format like '1m', '5m', '1h'")
    value, unit = int(match.group(1)), match.group(2)
    return value * STEP_UNIT_SECONDS[unit]


def execute_promql(prom_queries: Dict, expr: str, start_time, end_time, step) -> Dict:
    """ """
    step_seconds = parse_step_to_seconds(step)
    # query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    query_params = {
        "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
        "query_configs": [],
        "start_time": timezone2timestamp(start_time),
        "end_time": timezone2timestamp(end_time),
        "down_sample_range": step,
        "slimit": 5000,
        "type": "range",
        "expression": "",
        "alias": "AA",
    }

    query_config_one = {
        "alias": "aa",
        "promql": list(prom_queries.values())[0],
        "interval": step_seconds,
        "data_source_label": "prometheus",
        "data_type_label": "time_series",
    }
    if expr and "{" in expr and "}" in expr:
        query_config_one["promql"] = expr.format(**prom_queries)
        expr = ""  # 表达式再 promql 已渲染

    # query_params["query_configs"].append(query_config_one)
    query_params["query_configs"] = [query_config_one]
    if expr:
        query_params["expression"] = expr

    logger.info("query_promql_metrics promql: %s", prom_queries)
    resp = BKMonitorV3Api.unify_query(query_params)
    series = resp.get("series", [])
    return {
        "promql": prom_queries,
        "series": series,
    }
