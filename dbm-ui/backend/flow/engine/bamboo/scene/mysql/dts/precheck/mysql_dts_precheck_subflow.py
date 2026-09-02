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

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_str

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.dts.precheck.precheck_item import MysqlDtsPrecheckItemComponent
from backend.flow.utils.mysql.dts.precheck.base import all_items, get_item

# 阶段之间串联：上一阶段全部结束后才进入下一阶段。
# 同一阶段内并联：这些检查互不依赖，一项失败不挡住同阶段的其它项。
# 新检查项放进已有阶段，或在末尾追加一个新阶段。
CHECK_STAGES: list[list[str]] = [
    ["target_schema"],
    [
        "version",
        "advanced_objects",
        "binlog",
        "charset_collation",
        "instance_vars",
        "warnings",
    ],
]


def _act(code: str, data: dict) -> dict:
    item = get_item(code)
    return {
        "act_name": force_str(item.name),
        "act_component_code": MysqlDtsPrecheckItemComponent.code,
        "kwargs": {**data, "item_code": code},
    }


def _enabled_stages(enabled_codes: list[str] | None) -> list[list[str]]:
    known = [code for stage in CHECK_STAGES for code in stage]
    if len(known) != len(set(known)):
        raise ImproperlyConfigured("precheck stage contains a duplicated item")
    enabled = set(enabled_codes) if enabled_codes is not None else {item.code for item in all_items()}
    unknown = enabled - set(known)
    if unknown:
        raise ImproperlyConfigured(f"precheck item is not assigned to a stage: {sorted(unknown)}")
    return [[code for code in stage if code in enabled] for stage in CHECK_STAGES]


def mysql_dts_precheck_subflow(
    root_id: str,
    data: dict,
    enabled_codes: list[str] | None = None,
) -> SubBuilder:
    sub = SubBuilder(root_id=root_id, data=data)
    for stage in _enabled_stages(enabled_codes):
        if not stage:
            continue
        acts = [_act(code, data) for code in stage]
        if len(acts) == 1:
            sub.add_act(**acts[0])
            continue
        sub.add_parallel_acts(acts_list=acts)
    return sub
