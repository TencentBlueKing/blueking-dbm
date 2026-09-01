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
import threading
import uuid
from functools import wraps
from typing import Any, Callable, Hashable, Optional, Union

from cachetools import TTLCache
from django.core.cache import cache

from backend.utils.md5 import count_md5

DEFAULT_CACHE_TIME = 60 * 15


class LocalTTLCache:
    """
    进程内的 TTL 缓存，适用于变更极少但读取极频繁的元数据。

    与 django cache 的区别是不依赖 redis：redis 故障时这类查询会全部穿透到 mysql，
    正是需要兜底的场景。代价是各进程独立，写入方主动 clear 也只对本进程生效，
    其余进程最长在 ttl 后才能看到新数据，因此只适合能容忍 ttl 级别陈旧的数据。
    """

    def __init__(self, ttl: int, maxsize: int):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get_or_load(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        """
        读缓存，未命中时用 loader 回源并回填。

        回源过程刻意不持锁：worker 是 threads 池，持锁回源会让所有线程排队在一次回源上。
        代价是缓存失效瞬间同一进程可能有多个线程同时回源，相比穿透量级可以忽略。
        """
        with self._lock:
            try:
                return self._cache[key]
            except KeyError:
                pass

        value = loader()

        with self._lock:
            self._cache[key] = value

        return value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


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
