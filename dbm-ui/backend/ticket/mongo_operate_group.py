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


def expand_mongo_group(group) -> list:
    """把 'shard:1:s1,s2' 拆成单分片粒度 ['shard:1:s1', 'shard:1:s2']；缺分片名的残缺组返回空。"""
    if not group or not isinstance(group, str):
        return []
    if group.count(":") >= 2:
        kind, cid, rest = group.split(":", 2)
        if not kind or not cid:
            return []
        shards = sorted({name.strip() for name in rest.split(",") if name and name.strip()})
        if not shards:
            return []
        return [f"{kind}:{cid}:{shard}" for shard in shards]
    if group.endswith(":"):
        return []
    return [group]


def _expand_group_set(groups) -> set:
    if not groups:
        return set()
    expanded_all = set()
    for group in groups:
        if not group:
            continue
        expanded = expand_mongo_group(group)
        if not expanded:
            return set()
        for item in expanded:
            expanded_all.add(item)
            # config 替换/自愈会改集群内所有 mongos 的 configDB 参数，与 mongos 组互斥
            if item.startswith("config:"):
                parts = item.split(":", 2)
                if len(parts) >= 2 and parts[1]:
                    expanded_all.add(f"mongos:{parts[1]}")
    return expanded_all


def mongo_groups_allow_parallel(current_groups, other_groups) -> bool:
    """两边都带了分组且按分片展开后没有交集时允许并行。任一侧没有分组或含残缺分组则保持原集群互斥。"""
    current = _expand_group_set(current_groups)
    other = _expand_group_set(other_groups)
    if not current or not other:
        return False
    return current.isdisjoint(other)
