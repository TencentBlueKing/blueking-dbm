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
from rest_framework import serializers

from backend.db_meta.enums import MachineType
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_machine_type_choices


class ShowInstanceStatusesInputSerializer(serializers.Serializer):
    machine_type = serializers.ChoiceField(
        choices=mysql_machine_type_choices + [(MachineType.PROXY.value, MachineType.PROXY.name)],
        help_text=_("实例的机器类型, 只能是 [single, proxy, backend, remote, spider] 中之一"),
    )
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))


class InstanceRuntimeStatusSerializer(serializers.Serializer):
    status_name = serializers.CharField(help_text=_("运行时状态名"))
    status_value = serializers.CharField(help_text=_("运行时状态值"))


class ShowInstanceStatuesOutputSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    runtime_statuses = serializers.ListField(child=InstanceRuntimeStatusSerializer(), help_text=_("实例运行时状态列表"))
