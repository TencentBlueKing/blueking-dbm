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
from typing import Callable, Optional, Type


def get_class_from_qualname(func: Callable) -> Optional[Type]:
    """
    从函数的 __qualname__ 中获取所属的类
    """
    if not hasattr(func, "__qualname__"):
        return None

    qualname_parts = func.__qualname__.split(".")
    if len(qualname_parts) < 2:
        return None

    # 类名是倒数第二个部分
    class_name = qualname_parts[-2]
    module = importlib.import_module(func.__module__)
    if module:
        return getattr(module, class_name, None)

    return None
