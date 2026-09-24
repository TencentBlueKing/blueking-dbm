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
from typing import Dict, List

import promql_parser

# 查询过滤条件：维度名 -> 取值列表
QueryConditions = Dict[str, List[str]]


def extract_selector_matchers(expr) -> List[List[promql_parser.Matcher]]:
    """递归收集表达式中所有向量选择器的 label matchers，每个选择器一组"""
    if isinstance(expr, promql_parser.VectorSelector):
        return [list(expr.label_matchers)]
    if isinstance(expr, promql_parser.MatrixSelector):
        return extract_selector_matchers(expr.vector_selector)
    if isinstance(
        expr,
        (promql_parser.AggregateExpr, promql_parser.ParenExpr, promql_parser.UnaryExpr, promql_parser.SubqueryExpr),
    ):
        return extract_selector_matchers(expr.expr)
    if isinstance(expr, promql_parser.Call):
        return [matchers for arg in expr.args for matchers in extract_selector_matchers(arg)]
    if isinstance(expr, promql_parser.BinaryExpr):
        return extract_selector_matchers(expr.lhs) + extract_selector_matchers(expr.rhs)
    return []


def extract_conditions_from_promql(promql: str) -> List[QueryConditions]:
    """从 promql 中提取每个向量选择器的过滤条件，用于按选择器逐个鉴权"""
    ast = promql_parser.parse(promql)
    conditions_list = []
    for matchers in extract_selector_matchers(ast):
        conditions: QueryConditions = {}
        for match in matchers:
            # 同一维度出现多次时合并取值，避免只校验最后一个
            conditions.setdefault(match.name, []).append(match.value)
        conditions_list.append(conditions)
    return conditions_list
