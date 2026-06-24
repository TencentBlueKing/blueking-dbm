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
from typing import List, Type

from .base import BaseConfChecker

CHECKER_REGISTRY: List[BaseConfChecker] = []


def redis_conf_checker(cls: Type[BaseConfChecker]) -> Type[BaseConfChecker]:
    """Register a Redis conf checker. Decorate new checker subclasses; no manual list edits."""
    instance = cls()
    if not instance.name:
        raise ValueError(f"{cls.__name__} must set a non-empty name")
    if any(c.name == instance.name for c in CHECKER_REGISTRY):
        raise ValueError(f"duplicate redis conf checker name: {instance.name}")
    CHECKER_REGISTRY.append(instance)
    return cls


def get_candidate_cluster_types() -> List[str]:
    """Union of all checkers' cluster types - the clusters worth inspecting."""
    cluster_types = set()
    for checker in CHECKER_REGISTRY:
        cluster_types.update(checker.cluster_types)
    return list(cluster_types)


# Import every checker module here so @redis_conf_checker runs at import time.
# New checker modules must be imported here to complete registration.
from . import predixy_servers_checker as _predixy_servers_checker  # noqa: F401,E402
from . import role_checker as _role_checker  # noqa: F401,E402
