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

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 部分场景的版本无需特定，保持最新即可
LATEST = "latest"


# 新增数据库版本支持（比如MySQL9.0），大概率需要发版本初始化一些数据，如初始配置项等，甚至有流程的变更
# 且新增版本并非高频事件，因此这里暂时考虑使用枚举方式来维护，不存入数据库维护
class MySQLVersion(str, StructuredEnum):
    """MySQL数据库版本枚举"""

    MySQL56 = EnumField("MySQL-5.6", _("MySQL-5.6"))
    MySQL57 = EnumField("MySQL-5.7", _("MySQL-5.7"))
    MySQL80 = EnumField("MySQL-8.0", _("MySQL-8.0"))


class SpiderVersion(str, StructuredEnum):
    """Spider的版本枚举"""

    Spider1 = EnumField("Spider-1", _("Spider-1"))
    Spider3 = EnumField("Spider-3", _("Spider-3"))


class RedisVersion(str, StructuredEnum):
    """Redis-Cache数据库版本枚举"""

    Redis20 = EnumField("Redis-2", _("Redis-2"))
    Redis30 = EnumField("Redis-3", _("Redis-3"))
    Redis40 = EnumField("Redis-4", _("Redis-4"))
    Redis4t = EnumField("Redis-4t", _("Redis-4t"))
    Redis50 = EnumField("Redis-5", _("Redis-5"))
    Redis60 = EnumField("Redis-6", _("Redis-6"))
    Redis70 = EnumField("Redis-7", _("Redis-7"))


class TendisPlusVersion(str, StructuredEnum):
    """Redis-Plus数据库版本枚举"""

    TendisPlus25 = EnumField("Tendisplus-2.5", _("Tendisplus-2.5"))
    TendisPlus26 = EnumField("Tendisplus-2.6", _("Tendisplus-2.6"))


class TendisSsdVersion(str, StructuredEnum):
    """Redis-Plus数据库版本枚举"""

    TendisSsd12 = EnumField("TendisSSD-1.2", _("TendisSSD-1.2"))
    TendisSsd13 = EnumField("TendisSSD-1.3", _("TendisSSD-1.3"))


class TwemproxyVersion(str, StructuredEnum):
    """Twemproxy版本枚举"""

    TwemproxyLatest = EnumField("Twemproxy-latest", _("TwemproxyLatest"))


class PredixyVersion(str, StructuredEnum):
    """Predixy版本枚举"""

    PredixyLatest = EnumField("Predixy-latest", _("PredixyLatest"))
