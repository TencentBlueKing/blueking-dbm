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


class GetBizInternalModuleInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))


class BizInternalModuleSerializer(serializers.Serializer):
    bk_module_id = serializers.IntegerField(help_text=_("模块 ID"))
    bk_module_name = serializers.CharField(help_text=_("模块名称"))
    default = serializers.IntegerField(help_text=_("内置模块类型"))
    host_apply_enabled = serializers.BooleanField(help_text=_("是否启用主机属性自动应用"))


class GetBizInternalModuleOutputSerializer(serializers.Serializer):
    bk_set_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_set_name = serializers.CharField(help_text=_("集群名称"))
    module = serializers.ListField(child=BizInternalModuleSerializer(), help_text=_("内置模块列表"))
