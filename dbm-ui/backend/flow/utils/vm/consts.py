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


class VmConfigEnum(str, StructuredEnum):
    VmstorageRetentionPeriod = EnumField("vmstorage.retentionPeriod", _("数据过期时间"))
    VminsertReplicationFactor = EnumField("vminsert.replicationFactor", _("数据副本数"))


class VmMetaOperation(str, StructuredEnum):
    Add = EnumField("ADD", _("ADD"))
    Drop = EnumField("DROP", _("DROP"))
    Decommission = EnumField("DECOMMISSION", _("DECOMMISSION"))
    ForceDrop = EnumField("DROPP", _("DROPP"))


class VmNodeOperation(str, StructuredEnum):
    Start = EnumField("start", _("start"))
    Stop = EnumField("stop", _("stop"))
    Restart = EnumField("restart", _("restart"))


VMINSERT_STORAGE_PORT = 8400
VMSELECT_STORAGE_PORT = 8401
VM_DNS_PORT = 0
