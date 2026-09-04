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

    def build_promql(self) -> Dict[str, str]:
        """
        使用 promql-builder 根据自身参数构建 PromQL 查询字符串

        @return: 构建好的 PromQL 字符串
        """
        if not self.alias:
            self.alias = self.metric_name

        # 转换一下 metric_name
        if self.metric_name.startswith("mysql_"):
            self.metric_name = "bkmonitor:exporter_dbm_mysqld_exporter:__default__:" + self.metric_name
        elif not self.metric_name:
            raise ValueError("metric_name must be specified")
        elif not self.metric_name.startswith("bkmonitor:"):
            self.metric_name = "bkmonitor:dbm_system:" + self.metric_name

        # 1. 使用 promql-builder 构建 VectorExpr（metric + label 过滤）
        vector = promql.VectorExpr().metric(self.metric_name)

        if self.filters:
            for f in self.filters:
                label_name = f["label_name"]
                op = f["op"]
                value = f["value"]

                method_name = LABEL_OP_METHOD_MAP.get(op)
                if method_name is None:
                    raise ValueError(
                        f"Unsupported label operator: {op}, supported: {list(LABEL_OP_METHOD_MAP.keys())}"
                    )

                # 调用 VectorExpr 对应的 label 方法
                vector = getattr(vector, method_name)(label_name, value)

        # 2. 应用 range function（如果指定）
        if self.range_function:
            range_func = RANGE_FUNC_MAP.get(self.range_function)
            if range_func is None:
                raise ValueError(
                    f"Unsupported range_function: {self.range_function}, supported: {list(RANGE_FUNC_MAP.keys())}"
                )

            if not self.time_window:
                raise ValueError("time_window must be specified when using range_function")

            range_vector = vector.range(self.time_window)
            expr = range_func(range_vector)
        else:
            expr = vector

        # 3. 应用外层聚合函数（如果指定）
        if self.aggregation:
            agg_func = AGGREGATION_FUNC_MAP.get(self.aggregation)
            if agg_func is None:
                raise ValueError(
                    f"Unsupported aggregation function: {self.aggregation}, "
                    f"supported: {list(AGGREGATION_FUNC_MAP.keys())}"
                )
            agg_expr = agg_func(expr)
            if self.group_by:
                agg_expr = agg_expr.by(self.group_by)

            if self.aggregation_outer:
                # sum:cluster_domain,instance_role
                agg_outer_type, agg_outer_labels = self.aggregation_outer.split(":")
                agg_func_outer = AGGREGATION_FUNC_MAP.get(agg_outer_type)
                if agg_func_outer is None:
                    raise ValueError(
                        f"Unsupported aggregation function: {self.aggregation_outer}, "
                        f"supported: {list(AGGREGATION_FUNC_MAP.keys())}"
                    )
                agg_expr = agg_func_outer(agg_expr)
                if agg_outer_labels:
                    agg_expr = agg_expr.by(agg_outer_labels.split(","))
            promql_str = agg_expr.build()
        else:
            promql_str = expr.build()

        return {self.alias: str(promql_str)}

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
