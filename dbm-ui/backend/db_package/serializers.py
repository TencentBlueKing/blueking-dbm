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
from datetime import datetime

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.configuration.constants import DBType
from backend.db_package.constants import PackageType
from backend.db_package.models import Package


class PackageSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = "__all__"


class UploadPackageSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=_("版本包"))
    version = serializers.CharField(help_text=_("数据库版本"), required=False, allow_blank=True)
    pkg_type = serializers.ChoiceField(help_text=_("包类型"), choices=PackageType.get_choices())
    db_type = serializers.ChoiceField(help_text=_("存储类型"), choices=DBType.get_choices())


class SyncMediumSerializer(serializers.Serializer):
    class MediumDetailSerializer(serializers.ModelSerializer):
        create_at = serializers.DateTimeField(required=False, default=datetime.now(timezone.utc))
        update_at = serializers.DateTimeField(required=False, default=datetime.now(timezone.utc))

        class Meta:
            model = Package
            fields = "__all__"

    sync_medium_infos = serializers.ListSerializer(help_text=_("介质同步信息"), child=MediumDetailSerializer())
    db_type = serializers.ChoiceField(help_text=_("集群类型"), choices=DBType.get_choices())


class ListPackageVersionSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())
    query_key = serializers.ChoiceField(help_text=_("查询关键字"), choices=PackageType.get_choices())
