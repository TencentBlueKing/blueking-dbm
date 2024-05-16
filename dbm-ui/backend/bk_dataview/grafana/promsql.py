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

import promql_parser


def extract_condition_from_promql(promql):
    """从 promql 中提取 cluster_domain，目前仪表盘的设计"""
    ast = promql_parser.parse(promql)
    if hasattr(ast, "lhs"):
        expr = ast.lhs.expr
    else:
        expr = ast.expr
    matches = list(expr.args[0].vector_selector.label_matchers)
    return {match.name: match.value for match in matches}
