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
import os

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings
from django.utils.translation import ugettext as _

DB_MONITOR_TPLS_DIR = os.path.join(settings.BASE_DIR, "backend/db_monitor/tpls")
TPLS_COLLECT_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "collect")
TPLS_ALARM_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "alarm")

SWAGGER_TAG = "db_monitor"


class GroupType(str, StructuredEnum):
    """告警组类别: 平台级->业务级->集群级->一次性"""

    PLATFORM = EnumField("PLATFORM", _("platform"))
    APP = EnumField("APP", _("app"))
    CLUSTER = EnumField("CLUSTER", _("cluster"))
    SINGLE = EnumField("SINGLE", _("single"))


class TargetLevel(str, StructuredEnum):
    """告警策略类别: 平台级->业务级->模块级->集群级->实例级
    ROLE: 角色不确定所处的位置
    CUSTOM: 用于表达额外过滤条件
    """

    PLATFORM = EnumField("platform", _("platform"))
    APP = EnumField("app_id", _("app id"))
    MODULE = EnumField("db_module", _("db module"))
    CLUSTER = EnumField("cluster_domain", _("cluster domain"))
    CUSTOM = EnumField("custom", _("custom"))


class TargetPriority(int, StructuredEnum):
    """监控策略优先级: 0-10000"""

    PLATFORM = EnumField(0, _("platform"))
    APP = EnumField(1, _("app id"))
    MODULE = EnumField(10, _("db module"))
    CLUSTER = EnumField(100, _("cluster domain"))
    CUSTOM = EnumField(5000, _("custom"))


TARGET_LEVEL_TO_PRIORITY = {
    TargetLevel.PLATFORM.value: TargetPriority.PLATFORM,
    TargetLevel.APP.value: TargetPriority.APP,
    TargetLevel.MODULE.value: TargetPriority.MODULE,
    TargetLevel.CLUSTER.value: TargetPriority.CLUSTER,
    TargetLevel.CUSTOM.value: TargetPriority.CUSTOM,
}


class PolicyStatus(str, StructuredEnum):
    """监控策略状态"""

    VALID = EnumField("valid", _("有效"))
    TARGET_INVALID = EnumField("target_invalid", _("监控目标已失效"))
