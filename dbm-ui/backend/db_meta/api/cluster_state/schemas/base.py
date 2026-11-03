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
import copy
from typing import Any, Dict, Optional, Tuple

from backend.db_meta.api.cluster_state.fields.base import StateField


class ClusterStateSchemaMeta(type):
    """
    按 MRO 收集 StateField 属性并注入 key（字段类声明的 key 必须等于属性名）；子类将字段赋值为 None 表示移除继承来的字段。
    字段保留为类属性，可以直接通过 Schema.phase 访问，与 get_field("phase") 是同一个实例
    """

    def __new__(mcs, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]) -> "ClusterStateSchemaMeta":
        # 只在 Schema 类定义（模块 import）时执行一次，请求期间不会再进入
        state_fields: Dict[str, StateField] = {}
        # 先继承父类已收集好的字段，多继承时靠左的父类优先，与 MRO 一致
        for base in reversed(bases):
            state_fields.update(getattr(base, "_state_fields", {}))

        for attr, value in list(attrs.items()):
            if isinstance(value, StateField):
                mcs.check_not_shadowing(name, bases, attr)
                mcs.check_declared_key(name, attr, value)
                # 拷贝后再注入 key，避免同一个字段实例被多个 Schema 以不同属性名引用时 key 互相覆盖
                state_field = copy.copy(value)
                state_field.key = attr
                state_fields[attr] = state_field
                attrs[attr] = state_field
            elif value is None and attr in state_fields:
                state_fields.pop(attr)

        attrs["_state_fields"] = state_fields
        return super().__new__(mcs, name, bases, attrs)

    @staticmethod
    def check_not_shadowing(name: str, bases: Tuple[type, ...], attr: str) -> None:
        """字段名不能覆盖 Schema 自身的方法或属性（如 get_fields），否则 Schema 无法使用"""
        for base in bases:
            inherited = getattr(base, attr, None)
            if inherited is not None and not isinstance(inherited, StateField):
                raise TypeError(f"{name}.{attr}: state field name conflicts with {base.__name__}.{attr}")

    @staticmethod
    def check_declared_key(name: str, attr: str, state_field: StateField) -> None:
        """字段类声明了 key 时属性名必须与之一致，否则调用方用 Field.key 读写会找不到字段"""
        declared_key = type(state_field).key
        if declared_key and declared_key != attr:
            raise TypeError(
                f"{name}.{attr}: {type(state_field).__name__} declares key '{declared_key}', "
                f"attribute name must be the same"
            )


class ClusterStateSchema(metaclass=ClusterStateSchemaMeta):
    """
    集群状态声明：一个集群类型有哪些状态字段。只做声明，不写读写逻辑，类似 Django Model 之于 Field。

    写法（每个组件一个文件，放在 schemas/<组件>.py，由 registry.autodiscover 自动导入）：

        class MySQLHAStateSchema(CommonClusterStateSchema):      # 不注册的父类，供多个集群类型共用
            dbha_disabled = DBHADisabledField()                  # 属性名必须等于字段类声明的 key
            capacity = CapacityField(help_text=_("..."))         # 实例化时可覆盖字段属性（key 除外）

        @register_state_schema(cluster_types=[ClusterType.TenDBHA.value])
        class TenDBHAStateSchema(MySQLHAStateSchema):
            running_ticket = None                                # 赋值为 None 移除继承来的字段

    规则：
    - 一般继承 CommonClusterStateSchema 以获得公共字段（phase / status / running_ticket）
    - 一个集群类型只能被一个 Schema 注册，重复注册由 system check 报 cluster_state.E001
    - 字段名不能与 Schema 自身的方法重名；字段类声明了 key 时属性名必须与之一致，否则定义时抛 TypeError
    - 本类声明的字段会被拷贝一份再注入 key（字段类未声明 key 时即属性名）；继承来的字段与父类是同一个实例

    使用方一般不直接操作 Schema，读写都经 ClusterStateService，key 用字段类常量，如 CapacityField.key。
    """

    _state_fields: Dict[str, StateField] = {}

    @classmethod
    def get_fields(cls) -> Dict[str, StateField]:
        """全部字段 {key: StateField}，顺序与声明顺序一致（父类字段在前）"""
        return dict(cls._state_fields)

    @classmethod
    def get_field(cls, key: str) -> Optional[StateField]:
        """按 key 取字段，未声明时返回 None"""
        return cls._state_fields.get(key)
