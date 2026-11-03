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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class StateValueType(StrStructuredEnum):
    """状态字段的取值类型"""

    BOOL = EnumField("bool", _("布尔"))
    # 取值限定在 choices 内
    ENUM = EnumField("enum", _("枚举"))
    NUMBER = EnumField("number", _("数值"))
    # 自由字符串，不限定取值范围
    STR = EnumField("str", _("字符串"))
    # 一个集群同时有多个取值（列表），只允许 Native 字段使用；声明 choices 时元素限定在其中
    MULTI = EnumField("multi", _("多值"))


class StateStorageType(StrStructuredEnum):
    """Stored 字段在 ClusterState 表中的落库列：str -> state_str_value，int -> state_int_value"""

    STR = EnumField("str", _("字符串"))
    INT = EnumField("int", _("整数"))


class StateSource(StrStructuredEnum):
    """状态字段的数据来源"""

    NATIVE = EnumField("native", _("读取已有数据"))
    STORED = EnumField("stored", _("状态表存储"))


class StateFilterOperator(StrStructuredEnum):
    """列表过滤操作符，对应请求参数 state__{key}、state__{key}__gte、state__{key}__lte"""

    IN = EnumField("in", _("取值属于"))
    GTE = EnumField("gte", _("大于等于"))
    LTE = EnumField("lte", _("小于等于"))


class DrillDownType(StrStructuredEnum):
    """单元格下钻类型，前端按类型决定打开方式，下钻内容点击时通过详情接口获取"""

    INSTANCE_LIST = EnumField("INSTANCE_LIST", _("实例列表"))
    TICKET_LIST = EnumField("TICKET_LIST", _("单据列表"))
    LINK = EnumField("LINK", _("跳转链接"))
    DETAIL = EnumField("DETAIL", _("详情弹窗"))


class StateDetailType(StrStructuredEnum):
    """详情接口返回的展示形式"""

    KV = EnumField("kv", _("键值对"))
    TABLE = EnumField("table", _("表格"))
    TIMELINE = EnumField("timeline", _("时间线"))
