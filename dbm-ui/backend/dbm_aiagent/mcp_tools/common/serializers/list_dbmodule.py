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


class ListDBModulesInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id"))
    # cluster_type = serializers.CharField(help_text=_("集群类型"))


class DBModuleSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id"))
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("集群类型"))
    alias_name = serializers.CharField(help_text=_("别名, 用于生成域名"))
    db_module_id = serializers.IntegerField(help_text=_("dbmodule id"))
    charset = serializers.CharField(help_text=_("字符集"))
    db_version = serializers.CharField(help_text=_("db 版本"))


class ListDBModulesOutputSerializer(serializers.Serializer):
    dbmodules = serializers.ListSerializer(child=DBModuleSerializer(), help_text=_("dbmodule 列表"))
