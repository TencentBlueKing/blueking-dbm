"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import itertools


def custom_roundrobin(*iterables):
    """
    python3.10以上版本itertools才支持有roundrobin算法，目前使用版本不支持，故这里自建
    @param iterables: 任意数量的可迭代对象（如列表、集合等）
    """
    # 创建迭代器的循环队列
    next_s = itertools.cycle(iter(it) for it in iterables)
    # 循环直到所有迭代器耗尽
    while next_s:
        try:
            for it in next_s:
                yield next(it)
        except StopIteration:
            # 有耗尽的对象，剔除，重建列表
            next_s = itertools.cycle(itertools.islice(next_s, len(next_s) - 1))


def get_value_for_roundrobin(source_data: dict, max_size: int) -> set:
    """
    公平轮询取出函数，可控制最大迭代次数
    这是个通用函数，根据key:values的分组结构，公平轮询取出每个组的value
    比如分组结构有：
    key1: [A, B]
    key2: [1]
    key3: [X, Y, Z]
    如果想取出N个值，取出循序是：A->1->X->B->Y->Z ，直到长度等于N结束
    @param source_data: 数据源，结构必须要dict{key: list/set/tuple}
    @param max_size: 取出长度
    @return set, 返回结果保证去重
    """
    data_set = set()
    gens = [iter(values) for values in source_data.values() if values]
    # 轮询取值直到满足条件
    for value in itertools.islice(custom_roundrobin(*gens), max_size):
        if value not in data_set and len(data_set) < max_size:
            data_set.add(value)

    return data_set
