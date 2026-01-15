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
from backend.db_meta.enums import ClusterType


class ListBizsInputSerializer(serializers.Serializer):
    bk_biz_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("业务 ID 列表"), required=False)
    app_abbrs = serializers.ListField(child=serializers.CharField(), help_text=_("业务简称 列表"), required=False)


class BizDBComponentInfoSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(choices=DBType.get_choices(), help_text=_("集群技术栈类型"))
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("集群类型"))
    dbas = serializers.ListField(child=serializers.CharField(), help_text=_("dba 列表"))


class BizBaseInfoSerializer(serializers.Serializer):
    abbr = serializers.CharField(help_text=_("业务名, 简称"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    db_components = serializers.ListField(child=BizDBComponentInfoSerializer(), help_text=_("DB 组件列表"))


class ListBizsOutputSerializer(serializers.Serializer):
    bizs = serializers.ListField(child=BizBaseInfoSerializer(), help_text=_("业务列表"))
