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


class UpdateHostsOperatorInputSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text=_("主机 ID 列表"),
    )
    operators = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_("主负责人列表，对应 CMDB operator 字段"),
    )
    bak_operators = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_("备份负责人列表，对应 CMDB bk_bak_operator 字段"),
    )

    def validate(self, attrs):
        operators = [s.strip() for s in attrs.get("operators", []) if s.strip()]
        bak_operators = [s.strip() for s in attrs.get("bak_operators", []) if s.strip()]
        if not operators and not bak_operators:
            raise serializers.ValidationError(_("operators 与 bak_operators 不能同时为空"))

        attrs["operators"] = operators
        attrs["bak_operators"] = bak_operators
        attrs["bk_host_ids"] = list(set(attrs["bk_host_ids"]))
        return attrs


class UpdateHostsOperatorOutputSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("已更新的主机 ID 列表"),
    )
