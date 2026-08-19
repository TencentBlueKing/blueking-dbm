# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 摘要获取策略枚举。

模块职责：
    - 定义 :class:`SummaryFetchStrategy`，声明"读取某个维度摘要结果"时的取数策略
    - 该枚举落库到 :class:`PortraitDimensionRegistry.summary_fetch_strategy` 字段
"""
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

#: 维度评分权重的默认值，语义为「中等重要」。
#: 仅在 SDK/MCP 首次上报触发懒注册时作为 weight 的初始值落库；
#: 之后运维可在注册表上自由调整，SDK 不会覆盖。
#: 取值区间约定 0.1 ~ 1.0，0.5 为中等（默认）。
DEFAULT_DIMENSION_WEIGHT: float = 0.5


class SummaryFetchStrategy(StrStructuredEnum):
    """维度摘要获取策略。

    用于描述 :meth:`portrait_fetch_summaries` 在拉取某个巡检维度摘要时，
    时间范围内应返回哪些结果：

    - ``ALL``   ：获取时间范围内全部结果（默认）
    - ``LAST``  ：获取时间范围内时间上最新的一条结果
    - ``FIRST`` ：获取时间范围内时间上最老的一条结果
    """

    ALL = EnumField("all", _("获取全部结果"))
    LAST = EnumField("last", _("获取最新一条结果"))
    FIRST = EnumField("first", _("获取最老一条结果"))
