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
from typing import Any, List, Optional, Sequence

from django.apps import AppConfig
from django.core.checks import Error

from backend.db_meta.api.cluster_state.registry import get_registered_schemas, get_schema_conflicts


def check_cluster_state_schemas(app_configs: Optional[Sequence[AppConfig]] = None, **kwargs: Any) -> List[Error]:
    """
    校验各集群类型的状态声明，manage.py check 和服务启动时执行：
    cluster_state.E001 同一集群类型被多个 Schema 注册；cluster_state.E002 字段声明不完整，见 StateField.check
    """
    errors = [
        Error(
            f"cluster_type '{cluster_type}' is registered by both {registered.__name__} and {duplicated.__name__}",
            id="cluster_state.E001",
        )
        for cluster_type, registered, duplicated in get_schema_conflicts()
    ]
    for cluster_type, schema in get_registered_schemas().items():
        for key, state_field in schema.get_fields().items():
            errors.extend(
                Error(f"{schema.__name__}.{key}: {message}", obj=schema, id="cluster_state.E002")
                for message in state_field.check()
            )
    return errors
