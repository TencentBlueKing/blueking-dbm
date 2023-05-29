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

import json
import uuid
from functools import wraps
from typing import Any, Callable, Optional, Union

from django.core.cache import cache

from backend.utils.md5 import count_md5

DEFAULT_CACHE_TIME = 60 * 15


def class_member_cache(name: Optional[str] = None):
    """
    类成员缓存
    :param name: 缓存名称，为空则使用 class_func.__name__
    :return:
    """

    def class_member_cache_inner(class_func: Callable) -> Callable:
        @wraps(class_func)
        def wrapper(self, *args, **kwargs):

            cache_field = f"_{name or class_func.__name__}"

            cache_member = getattr(self, cache_field, None)
            if cache_member:
                return cache_member
            cache_member = class_func(self, *args, **kwargs)
            setattr(self, cache_field, cache_member)
            return cache_member

        return wrapper

    return class_member_cache_inner


def format_cache_key(func: Callable, *args, **kwargs):
    """计算缓存的key，通过函数名加上参数md5值得到"""
    kwargs.update({"args": args})
    return f"{func.__name__}_{count_md5(kwargs)}"


def func_cache_decorator(cache_time: int = DEFAULT_CACHE_TIME):
    """
    函数缓存装饰器
    :param cache_time: 缓存时间
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            get_cache = kwargs.pop("get_cache", False)
            cache_key = format_cache_key(func, *args, **kwargs)
            func_result = None
            if get_cache:
                func_result = cache.get(cache_key, None)

            # 若无需从缓存中获取数据或者缓存中没有数据，则执行函数得到结果，并设置缓存
            if func_result is None:
                func_result = func(*args, **kwargs)
                cache.set(cache_key, json.dumps(func_result), cache_time)
            else:
                func_result = json.loads(func_result)
            return func_result

        return wrapper

    return decorate


def data_cache(key: Union[str, None], data: Any, cache_time: int = DEFAULT_CACHE_TIME) -> str:
    """
    数据缓存
    :param key: 缓存键，如果为空则自动生成uid
    :param data: 将要缓存的数据
    :param cache_time: 缓存时间
    """

    data_key = key or uuid.uuid1().hex
    cache.set(data_key, data, cache_time)
    return data_key
