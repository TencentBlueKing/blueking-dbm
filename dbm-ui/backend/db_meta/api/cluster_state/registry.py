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
import importlib
import pkgutil
from typing import Callable, Dict, List, Optional, Tuple, Type, TypeVar

from backend.db_meta.api.cluster_state import schemas
from backend.db_meta.api.cluster_state.schemas.base import ClusterStateSchema

SchemaT = TypeVar("SchemaT", bound=Type[ClusterStateSchema])

_schema_registry: Dict[str, Type[ClusterStateSchema]] = {}
# (cluster_type, 已注册的 Schema, 重复注册的 Schema)，由 system check 报错
_schema_conflicts: List[Tuple[str, Type[ClusterStateSchema], Type[ClusterStateSchema]]] = []
_discovered = False


def register_state_schema(cluster_types: List[str]) -> Callable[[SchemaT], SchemaT]:
    """
    类装饰器，把 Schema 注册到一个或多个集群类型，原样返回被装饰的类。
    一个集群类型只能注册一个 Schema，重复注册不抛异常，保留先注册的并记录冲突，由 system check 报 cluster_state.E001
    """

    def decorator(schema_cls: SchemaT) -> SchemaT:
        for cluster_type in cluster_types:
            registered = _schema_registry.get(cluster_type)
            if registered and registered is not schema_cls:
                _schema_conflicts.append((cluster_type, registered, schema_cls))
                continue
            _schema_registry[cluster_type] = schema_cls
        return schema_cls

    return decorator


def autodiscover() -> None:
    """导入 schemas 包下所有组件模块（mysql.py 等），触发其中的 register_state_schema；只执行一次"""
    global _discovered
    if _discovered:
        return
    for module in pkgutil.iter_modules(schemas.__path__):
        importlib.import_module(f"{schemas.__name__}.{module.name}")
    _discovered = True


def get_schema(cluster_type: str) -> Optional[Type[ClusterStateSchema]]:
    """集群类型注册的 Schema，未接入状态框架时返回 None"""
    autodiscover()
    return _schema_registry.get(cluster_type)


def get_registered_schemas() -> Dict[str, Type[ClusterStateSchema]]:
    """全部注册关系 {cluster_type: Schema}"""
    autodiscover()
    return dict(_schema_registry)


def get_schema_conflicts() -> List[Tuple[str, Type[ClusterStateSchema], Type[ClusterStateSchema]]]:
    """重复注册的记录 [(cluster_type, 已注册的 Schema, 重复注册的 Schema)]"""
    autodiscover()
    return list(_schema_conflicts)
