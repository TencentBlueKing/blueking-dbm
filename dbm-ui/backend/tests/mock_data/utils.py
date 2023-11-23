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

from typing import Any, Callable, Optional, Union

import wrapt

from blue_krill.data_types.enum import StructuredEnum


class MockReturnType(StructuredEnum):

    RETURN_VALUE = ("return_value", "直接返回指定data")
    SIDE_EFFECT = ("side_effect", "返回可调用函数")


class MockReturn:
    return_type: str = None
    return_obj: Optional[Union[Callable, Any]] = None

    def __init__(self, return_type: str, return_obj: Union[Callable, Any]):
        if return_type not in MockReturnType.field_members:
            raise ValueError(f"except return type -> {MockReturnType.field_members}, but get {return_type}")
        self.return_type = return_type

        if self.return_type == MockReturnType.SIDE_EFFECT.value:
            if not callable(return_obj):
                raise ValueError(f"return_obj must be callable because return type is {self.return_type}")
        self.return_obj = return_obj


@wrapt.decorator
def raw_response(wrapped, instance, args, kwargs):
    """根据raw参数来决定是否返回原始的response"""

    data = wrapped(*args, **kwargs)
    raw_resp = {"code": 0, "message": "ok", "data": data}
    if kwargs.get("raw", False):
        return raw_resp

    return data
