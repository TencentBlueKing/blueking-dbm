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
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from multiprocessing.pool import ThreadPool
from typing import Callable

import wrapt
from django.conf import settings
from django.utils.translation import get_language

from backend.core.translation.context import RespectsLanguage
from backend.utils.local import local

QUERY_CMDB_LIMIT = 500
WRITE_CMDB_LIMIT = 500
QUERY_CMDB_MODULE_LIMIT = 500
QUERY_CLOUD_LIMIT = 200


def inject_request(func: Callable):
    request = local.request

    def inner(*args, **kwargs):
        if request:
            local.request = request
        return func(*args, **kwargs)

    return inner


def format_params(params, get_count, func, start_key, limit_key):
    # 拆分params适配bk_module_id大于500情况
    request_params = []

    bk_module_ids = params.pop("bk_module_ids", [])

    # 请求第一次获取总数
    if not bk_module_ids:
        request_params.append(
            {"count": get_count(func(page={start_key: 0, limit_key: 1}, **params)), "params": params}
        )

    for s_index in range(0, len(bk_module_ids), QUERY_CMDB_MODULE_LIMIT):
        single_params = deepcopy(params)

        single_params.update({"bk_module_ids": bk_module_ids[s_index : s_index + QUERY_CMDB_MODULE_LIMIT]})
        request_params.append(
            {"count": get_count(func(page={start_key: 0, limit_key: 1}, **single_params)), "params": single_params}
        )

    return request_params


def batch_request(
    func,
    params,
    start_key="start",
    limit_key="limit",
    get_data=lambda x: x["info"],
    get_count=lambda x: x["count"],
    limit=QUERY_CMDB_LIMIT,
    sort=None,
    split_params=False,
):
    """
    异步并发请求接口
    :param func: 请求方法
    :param params: 请求参数
    :param start_key: 分页起始key
    :param limit_key: 分页最大数key
    :param get_data: 获取数据函数
    :param get_count: 获取总数函数
    :param limit: 一次请求数量
    :param sort: 排序
    :param split_params: 是否拆分参数
    :return: 请求结果
    """

    # 如果该接口没有返回count参数，只能同步请求
    if not get_count:
        return sync_batch_request(func, params, get_data, limit, start_key, limit_key)

    if not split_params:
        final_request_params = [
            {"count": get_count(func(dict(page={start_key: 0, limit_key: 1}, **params))), "params": params}
        ]
    else:
        final_request_params = format_params(params, get_count, func, start_key, limit_key)

    data = []

    # 根据请求总数并发请求
    pool = ThreadPool(settings.CONCURRENT_NUMBER)
    futures = []

    for req in final_request_params:
        start = 0
        while start < req["count"]:
            request_params = {"page": {limit_key: limit, start_key: start}}
            if sort:
                request_params["page"]["sort"] = sort
            request_params.update(req["params"])
            futures.append(pool.apply_async(inject_request(func), args=(request_params,)))

            start += limit

    pool.close()
    pool.join()

    # 取值
    for future in futures:
        data.extend(get_data(future.get()))

    return data


def sync_batch_request(func, params, get_data=lambda x: x["info"], limit=500, start_key="start", limit_key="limit"):
    """
    同步请求接口
    :param func: 请求方法
    :param params: 请求参数
    :param get_data: 获取数据函数
    :param limit: 一次请求数量
    :param start_key: 分页起始key
    :param limit_key: 分页最大数key
    :return: 请求结果
    """
    # 如果该接口没有返回count参数，只能同步请求
    data = []
    start = 0

    # 根据请求总数并发请求
    while True:
        request_params = {"page": {limit_key: limit, start_key: start}}
        request_params.update(params)
        result = get_data(func(request_params))
        data.extend(result)
        if len(result) < limit:
            break
        else:
            start += limit

    return data


def request_multi_thread(func, params_list, get_data=lambda x: []):
    """
    并发请求接口，每次按不同参数请求最后叠加请求结果
    :param func: 请求方法
    :param params_list: 参数列表
    :param get_data: 获取数据函数，通常CMDB的批量接口应该设置为 get_data=lambda x: x["info"]，其它场景视情况而定
    :return: 请求结果累计
    """
    # 参数预处理，添加request_id

    for params in params_list:
        if "params" in params:
            params["params"]["_request"] = local.request

    result = []
    with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
        tasks = [ex.submit(RespectsLanguage(language=get_language())(func), **params) for params in params_list]
    for future in as_completed(tasks):
        result.append(get_data(future.result()))
    return result


def batch_decorator(
    batch=True,
    is_classmethod=False,
    start_key="start",
    limit_key="limit",
    get_data=lambda x: x["info"],
    get_count=lambda x: x["count"],
):
    """
    批量请求装饰器：要求调用方需要将所有参数以kwargs传递, args保留用于cls，self这些类变量
    @param batch: 是否启用批量查询
    @param is_classmethod: 是否是类方法
    @param start_key: 分页起始key
    @param limit_key: 分页最大数key
    @param get_count: 接口请求数量的获取函数
    @param get_data: 接口请求数据的获取函数
    """

    def func_inject_params(params):
        func = params.pop("wrapped")
        return func(**params)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if kwargs["page"][limit_key] != -1 or not batch:
            return wrapped(*args, **kwargs)

        kwargs.pop("page")
        kwargs.update(wrapped=wrapped)
        # 如果是classmethod，默认为第一个位置参数
        if is_classmethod:
            kwargs.update(cls=args[0])

        # 调用批量请求接口
        data = batch_request(
            func=func_inject_params,
            params=kwargs,
            get_data=get_data,
            get_count=get_count,
            start_key=start_key,
            limit_key=limit_key,
        )
        return {"data": data, "total": len(data)}

    return wrapper
