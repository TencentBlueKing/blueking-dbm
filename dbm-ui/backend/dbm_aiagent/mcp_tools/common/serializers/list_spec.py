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

from backend.configuration.constants import DBType
from backend.db_meta.enums.spec import SpecMachineType


class ListSpecInputSerializer(serializers.Serializer):
    spec_cluster_type = serializers.ChoiceField(choices=DBType.get_choices(), help_text=_("组件类型"), required=False)
    spec_machine_type = serializers.ChoiceField(
        choices=SpecMachineType.get_choices(), help_text=_("机器类型"), required=False
    )
    spec_name = serializers.CharField(help_text=_("规格名称关键字，模糊匹配"), required=False)
    cpu = serializers.IntegerField(help_text=_("CPU 核数，按规格 CPU 范围 [min, max] 包含匹配"), required=False)
    mem = serializers.IntegerField(help_text=_("内存大小(GB)，按规格内存范围 [min, max] 包含匹配"), required=False)
    storage = serializers.IntegerField(
        help_text=_("/data 单盘容量(GB)，按规格 /data 单盘范围 [min, max] 包含匹配；不含 /data 挂载点的规格将不会被匹配到"),
        required=False,
    )


class SpecItemSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格 ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    spec_cluster_type = serializers.CharField(help_text=_("组件类型"))
    spec_machine_type = serializers.CharField(help_text=_("机器类型"))
    spec_cluster_type_name = serializers.CharField(help_text=_("组件类型名称"))
    spec_machine_type_name = serializers.CharField(help_text=_("机器类型名称"))
    cpu = serializers.JSONField(help_text=_("CPU 规格描述"))
    mem = serializers.JSONField(help_text=_("内存规格描述"))
    storage_spec = serializers.JSONField(help_text=_("磁盘规格描述"))
    biz_scope = serializers.JSONField(help_text=_("业务范围，空列表表示全部业务"))


class ListSpecOutputSerializer(serializers.Serializer):
    specs = serializers.ListSerializer(child=SpecItemSerializer(), help_text=_("已启用规格列表"))
