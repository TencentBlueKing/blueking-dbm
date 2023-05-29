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
import abc
from enum import Enum
from typing import Any, Dict, List, Tuple

from ..utils.cache import class_member_cache


class EnhanceEnum(Enum):
    """增强枚举类，提供常用的枚举值列举方法"""

    @classmethod
    @abc.abstractmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        """
        获取枚举成员与释义的映射关系
        :return:
        """
        raise NotImplementedError

    @classmethod
    @class_member_cache()
    def list_member_values(cls) -> List[Any]:
        """
        获取所有的枚举成员值
        :return:
        """
        member_values = []
        for member in cls._member_names_:
            member_values.append(cls._member_map_[member].value)
        return member_values

    @classmethod
    @class_member_cache()
    def get_member_value__alias_map(cls) -> Dict[Any, str]:
        """
        获取枚举成员值与释义的映射关系，缓存计算结果
        :return:
        """
        member_value__alias_map = {}
        member__alias_map = cls._get_member__alias_map()

        for member, alias in member__alias_map.items():
            if type(member) is not cls:
                raise ValueError(f"except member type -> {cls}, but got -> {type(member)}")
            member_value__alias_map[member.value] = alias

        return member_value__alias_map

    @classmethod
    @class_member_cache()
    def list_choices(cls) -> List[Tuple[Any, Any]]:
        """
        获取可选项列表，一般用于序列化器、model的choices选项
        :return:
        """
        return list(cls.get_member_value__alias_map().items())
