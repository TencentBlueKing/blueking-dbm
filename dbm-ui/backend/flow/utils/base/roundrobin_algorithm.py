"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


class RoundrobinSizeMismatchError(Exception):
    """
    轮询结果长度与期望长度不一致时抛出。
    通常意味着输入分组的去重后总元素数 < max_size，不满足业务对取值数量的硬性要求。
    """

    def __init__(self, max_size: int, actual_size: int, source_keys=None):
        self.max_size = max_size
        self.actual_size = actual_size
        self.source_keys = list(source_keys) if source_keys is not None else []
        super().__init__(
            f"roundrobin result size mismatch: expected={max_size}, actual={actual_size}, "
            f"source_keys={self.source_keys}"
        )


def custom_roundrobin(*iterables):
    """
    公平轮询生成器：依次从每个可迭代对象取一个元素，耗尽的对象自动剔除，直到全部耗尽。
    python3.10以上版本itertools才支持有roundrobin算法，目前使用版本不支持，故这里自建
    @param iterables: 任意数量的可迭代对象（如列表、集合等）

    示例：
    custom_roundrobin([A, B], [1], [X, Y, Z]) -> A, 1, X, B, Y, Z
    """
    # 维护一个"活跃迭代器"列表，使用 sentinel 检测耗尽，避免依赖 StopIteration 控制流。
    iterators = [iter(it) for it in iterables]
    sentinel = object()
    while iterators:
        next_round = []
        for it in iterators:
            value = next(it, sentinel)
            if value is sentinel:
                # 当前迭代器已耗尽，不再加入下一轮
                continue
            yield value
            next_round.append(it)
        iterators = next_round


def get_value_for_roundrobin(source_data: dict, max_size: int, strict: bool = True) -> set:
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
    @param strict: 是否启用严格校验。默认 True，即返回 set 长度必须 == max_size，
                   否则抛出 RoundrobinSizeMismatchError；置为 False 时与旧行为一致，
                   仅返回能取到的去重元素。
    @return set, 返回结果保证去重

    边界说明：
    - max_size <= 0 或 source_data 为空时：strict=True 抛异常；strict=False 返回空集合；
    - 当所有有效分组的元素总数（去重后）少于 max_size 时：strict=True 抛异常；
      strict=False 返回所有可取到的去重元素。
    """
    data_set: set = set()
    if max_size > 0 and source_data:
        gens = [iter(values) for values in source_data.values() if values]
        # 轮询取值，遇到重复元素跳过，直到达到 max_size 或所有迭代器耗尽
        for value in custom_roundrobin(*gens):
            if value not in data_set:
                data_set.add(value)
                if len(data_set) >= max_size:
                    break

    if strict and len(data_set) != max_size:
        raise RoundrobinSizeMismatchError(
            max_size=max_size,
            actual_size=len(data_set),
            source_keys=list(source_data.keys()) if source_data else [],
        )

    return data_set
