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
from backend.db_package.constants import PackageType
from backend.db_services.version.constants import SqlserverVersion


class ListVersionSerializer(serializers.Serializer):
    query_key = serializers.ChoiceField(
        help_text=_("查询关键字"), choices=ClusterType.get_choices() + PackageType.get_choices()
    )


class ListSQLServerSystemVersionSerializer(serializers.Serializer):
    sqlserver_version = serializers.ChoiceField(help_text=_("数据库版本"), choices=SqlserverVersion.get_choices())
