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
from dataclasses import dataclass

COMPARE_BOOL = "bool"
KIND_ABSENT = "absent"
KIND_DIFFERENT = "different"

_TRUE_TOKENS = {"on", "1", "true"}
_FALSE_TOKENS = {"off", "0", "false"}


class Absent:
    """变量在该实例的返回里不存在。"""

    def __repr__(self) -> str:
        return "ABSENT"

    def __eq__(self, other) -> bool:
        return isinstance(other, Absent)

    def __hash__(self) -> int:
        return hash(Absent)


ABSENT = Absent()


@dataclass(frozen=True)
class ConsistencyVar:
    name: str
    compare: str


@dataclass(frozen=True)
class InstanceVarMap:
    ip: str
    port: int
    variables: dict


@dataclass(frozen=True)
class Mismatch:
    name: str
    kind: str
    rows: tuple


CHECKED_VARS = (
    ConsistencyVar("innodb_large_prefix", COMPARE_BOOL),
    ConsistencyVar("innodb_strict_mode", COMPARE_BOOL),
    ConsistencyVar("rocksdb_large_prefix", COMPARE_BOOL),
    ConsistencyVar("rocksdb_strict_collation_check", COMPARE_BOOL),
)


def normalize(var: ConsistencyVar, raw):
    if raw is None:
        return ABSENT
    if var.compare != COMPARE_BOOL:
        return str(raw)
    return _normalize_bool(str(raw))


def diff_remote_masters(var_maps_by_instance: list) -> list:
    """比较已取回的主分片变量。查询失败不进这里。"""
    if len(var_maps_by_instance) <= 1:
        return []
    mismatches = []
    for var in CHECKED_VARS:
        normalized = [normalize(var, _lookup(instance.variables, var.name)) for instance in var_maps_by_instance]
        mismatch = _mismatch_for(var.name, var_maps_by_instance, normalized)
        if mismatch is not None:
            mismatches.append(mismatch)
    return mismatches


def _normalize_bool(raw: str) -> str:
    token = raw.strip().casefold()
    if token in _TRUE_TOKENS:
        return "on"
    if token in _FALSE_TOKENS:
        return "off"
    return raw


def _lookup(variables: dict, name: str):
    for key, value in variables.items():
        if str(key).lower() == name:
            return value
    return None


def _mismatch_for(name: str, instances: list, normalized: list):
    if all(value is ABSENT for value in normalized):
        return None
    if any(value is ABSENT for value in normalized):
        kind = KIND_ABSENT
    elif len(set(normalized)) > 1:
        kind = KIND_DIFFERENT
    else:
        return None
    rows = tuple(_row(instance, name, value) for instance, value in zip(instances, normalized))
    return Mismatch(name=name, kind=kind, rows=rows)


def _row(instance: InstanceVarMap, name: str, normalized):
    if normalized is ABSENT:
        return (instance.ip, instance.port, ABSENT)
    return (instance.ip, instance.port, _lookup(instance.variables, name))
