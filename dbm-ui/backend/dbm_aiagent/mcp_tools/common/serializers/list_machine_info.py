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

from backend.db_meta.models.machine import Machine


class ListMachineInfoInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), default=None)
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("IP 列表"))


class MachineInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        exclude = ["creator", "create_at", "updater", "update_at"]


class AmbiguousIPSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("IP 地址"))
    bk_cloud_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("该 IP 所在的云区域 ID 列表"))


class ListMachineInfoOutputSerializer(serializers.Serializer):
    machines = serializers.ListSerializer(child=MachineInfoSerializer(), help_text=_("机器列表"))
    not_found_ips = serializers.ListField(child=serializers.CharField(), help_text=_("未找到的 IP 列表"))
    ambiguous_ips = serializers.ListSerializer(
        child=AmbiguousIPSerializer(), help_text=_("存在于多个云区域的 IP, 需指定 bk_cloud_id 区分")
    )
