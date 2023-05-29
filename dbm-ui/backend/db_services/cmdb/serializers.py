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

from backend.db_meta.enums import ClusterType


class BIZSLZ(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    name = serializers.CharField(help_text=_("业务名"))
    english_name = serializers.CharField(help_text=_("业务英文名"))
    permission = serializers.JSONField(help_text=_("业务权限列表"))


class ModuleSLZ(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    name = serializers.CharField(help_text=_("DB模块名"))


class ListModulesSLZ(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class CreateModuleSLZ(serializers.Serializer):
    db_module_name = serializers.CharField(help_text=_("DB模块名"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class SetBkAppAbbrSLZ(serializers.Serializer):
    db_app_abbr = serializers.CharField(help_text=_("英文缩写"))


class TopoSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class ListNodesSerializer(TopoSerializer):
    limit = serializers.IntegerField(help_text=_("单页数量"))
    page = serializers.IntegerField(help_text=_("页数"))
    module_id = serializers.IntegerField(help_text=_("模块ID"), required=False)
    set_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
