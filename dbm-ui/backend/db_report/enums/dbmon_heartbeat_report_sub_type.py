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


class DbmonHeartbeatReportSubType(str, StructuredEnum):
    TWEMPROXY = EnumField("TWEMPROXY", _("TWEMPROXY"))
    PREDIXY = EnumField("PREDIXY", _("PREDIXY"))
    REDIS_SSD = EnumField("REDIS_SSD", _("REDIS_SSD"))
    REDIS_CACHE = EnumField("REDIS_CACHE", _("REDIS_CACHE"))
    TENDISPLUS = EnumField("TENDISPLUS", _("TENDISPLUS"))
