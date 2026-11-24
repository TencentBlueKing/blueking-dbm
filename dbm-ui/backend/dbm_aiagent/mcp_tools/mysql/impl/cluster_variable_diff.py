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
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# 仅依赖同目录取数模块中的忽略键常量与 flow 公共对比引擎；取数函数在入口包装里惰性导入，便于纯函数单测。
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import IGNORED_RUNTIME_VARIABLE_KEYS
from backend.flow.utils.mysql.cluster_variables.diff import HIGH_IMPACT_KEYS, PER_INSTANCE_VARIABLE_KEYS
from backend.flow.utils.mysql.cluster_variables.diff import (
    build_tendbcluster_variable_diff as _build_tendbcluster_variable_diff,
)
from backend.flow.utils.mysql.cluster_variables.diff import build_tendbha_variable_diff as _build_tendbha_variable_diff
from backend.flow.utils.mysql.cluster_variables.diff import diff_variables as _diff_variables

# 可自定义：额外忽略的精确变量名（小写匹配）。在此追加业务侧不想对比的键。
EXTRA_IGNORE_VARIABLE_KEYS: frozenset[str] = frozenset(
    {
        "read_only",
        "super_read_only",
    }
)

# 可自定义：额外忽略的变量名前缀（小写 startswith）。在此追加前缀。
# 注：myisam_ / performance_schema_ 等已在 cluster_runtime_variables 取数时过滤，此处不必重复。
EXTRA_IGNORE_VARIABLE_PREFIXES: Tuple[str, ...] = (
    # 例: "spider_auto_increment_",
)


def _lower_key_set(keys) -> frozenset:
    return frozenset(k.lower() for k in keys)


def should_skip_variable(name: str) -> bool:
    """判断变量是否应在对比中跳过（天然不同 / 额外忽略键 / 前缀）。"""
    lname = (name or "").lower()
    if not lname:
        return True
    if lname in _lower_key_set(IGNORED_RUNTIME_VARIABLE_KEYS):
        return True
    if lname in _lower_key_set(PER_INSTANCE_VARIABLE_KEYS):
        return True
    if lname in _lower_key_set(EXTRA_IGNORE_VARIABLE_KEYS):
        return True
    for prefix in EXTRA_IGNORE_VARIABLE_PREFIXES:
        if prefix and lname.startswith(prefix.lower()):
            return True
    return False


def diff_variables(left_vars: Dict[str, Any], right_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
    """双方共有键逐项对比；仅一侧存在的键不报 mismatch。"""
    return _diff_variables(
        left_vars,
        right_vars,
        should_skip=should_skip_variable,
        high_impact_keys=HIGH_IMPACT_KEYS,
    )


def build_tendbha_variable_diff(runtime_data: Dict, cluster_domain: str = "") -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 HA 差异。"""
    return _build_tendbha_variable_diff(
        runtime_data,
        cluster_domain=cluster_domain,
        should_skip=should_skip_variable,
        high_impact_keys=HIGH_IMPACT_KEYS,
    )


def build_tendbcluster_variable_diff(runtime_data: Dict, cluster_domain: str = "") -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 Cluster 差异（紧凑结构）。"""
    return _build_tendbcluster_variable_diff(
        runtime_data,
        cluster_domain=cluster_domain,
        spider_should_skip=should_skip_variable,
        shard_should_skip=should_skip_variable,
        spider_high_impact_keys=HIGH_IMPACT_KEYS,
        shard_high_impact_keys=HIGH_IMPACT_KEYS,
    )


def tendbha_master_slave_variable_diff(cluster_obj) -> Dict:
    from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import cluster_runtime_variables

    runtime = cluster_runtime_variables(cluster_obj)
    return build_tendbha_variable_diff(runtime, cluster_domain=cluster_obj.immute_domain or "")


def tendbcluster_variable_diff(cluster_obj) -> Dict:
    from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import cluster_runtime_variables

    runtime = cluster_runtime_variables(cluster_obj)
    return build_tendbcluster_variable_diff(runtime, cluster_domain=cluster_obj.immute_domain or "")
