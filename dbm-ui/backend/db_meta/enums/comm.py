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


class SyncType(StrStructuredEnum):
    MS = EnumField("ms", _("ms"))
    SMS = EnumField("sms", _("sms"))
    MMS = EnumField("mms", _("mms"))


class DBCCModule(StrStructuredEnum):
    REDIS = EnumField("redis", _("redis"))
    MONGODB = EnumField("mongodb", _("mongodb"))


class RedisVerUpdateNodeType(StrStructuredEnum):
    """redis版本升级节点类型"""

    Proxy = EnumField("Proxy", _("Proxy"))
    Backend = EnumField("Backend", _("Backend"))


class TagType(StrStructuredEnum):
    """标签类型"""

    RESOURCE = EnumField("resource", _("资源标签"))
    CLUSTER = EnumField("cluster", _("集群标签"))


class SystemTagEnum(StrStructuredEnum):
    """系统内置的tag名称"""

    TEMPORARY = EnumField("temporary", _("临时集群"))
