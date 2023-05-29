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


class GroupType(str, StructuredEnum):
    """告警组类别: 平台级->业务级->集群级->一次性"""

    PLATFORM = EnumField("PLATFORM", _("platform"))
    APP = EnumField("APP", _("app"))
    CLUSTER = EnumField("CLUSTER", _("cluster"))
    SINGLE = EnumField("SINGLE", _("single"))
