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

from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.configuration.constants import DBType
from backend.db_package.models import Package


class PackageSerializer(AuditedSerializer, serializers.ModelSerializer):
    instances = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Package
        fields = "__all__"

    @property
    def instances_map(self):
        if not hasattr(self, "_instances_map"):
            # 优先使用 context 中传入的 instances_map（避免 N+1 查询）
            if self.context and "instances_map" in self.context:
                self._instances_map = self.context["instances_map"]
            else:
                # 如果没有传入，则自己查询
                if isinstance(self.instance, list):
                    package_ids = [pkg.id for pkg in self.instance]
                else:
                    package_ids = [self.instance.id]
                package_stats = (
                    Package.objects.filter(id__in=package_ids)
                    .annotate(
                        instances=Count("storageinstance", distinct=True) + Count("proxyinstance", distinct=True)
                    )
                    .values("id", "instances")
                )
                # 构建映射字典：package_id -> 实例总数
                self._instances_map = {item["id"]: item["instances"] for item in package_stats}

        return self._instances_map

    def get_instances(self, obj):
        return self.instances_map.get(obj.id, 0)


class UploadPackageSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=_("版本包"))
    version = serializers.CharField(help_text=_("数据库版本"), required=False, allow_blank=True)
    pkg_type = serializers.CharField(help_text=_("包类型"))
    db_type = serializers.ChoiceField(help_text=_("存储类型"), choices=DBType.get_choices())


class SyncMediumSerializer(serializers.Serializer):
    class MediumDetailSerializer(serializers.ModelSerializer):
        create_at = serializers.DateTimeField(required=False, default=datetime.now(timezone.utc))
        update_at = serializers.DateTimeField(required=False, default=datetime.now(timezone.utc))
        pkg_type = serializers.CharField(help_text=_("包类型"), required=False)
        distribution_name = serializers.CharField(help_text=_("发行版"), required=False, default="DBM", allow_blank=True)
        distribution_engine = serializers.CharField(help_text=_("引擎"), required=False, default="", allow_blank=True)
        version_series = serializers.CharField(help_text=_("版本系列"), required=False, default="", allow_blank=True)
        phase = serializers.CharField(help_text=_("阶段"), required=False, default="release", allow_blank=True)
        description = serializers.CharField(help_text=_("描述"), required=False, default="", allow_blank=True)
        full_version = serializers.CharField(
            help_text=_("完整版本"), required=False, default="1.0.0.0.0.0", allow_blank=True
        )
        version_name = serializers.CharField(help_text=_("版本名称"), required=False, default="", allow_blank=True)

        class Meta:
            model = Package
            fields = "__all__"

    sync_medium_infos = serializers.ListSerializer(help_text=_("介质同步信息"), child=MediumDetailSerializer())
    db_type = serializers.ChoiceField(help_text=_("集群类型"), choices=DBType.get_choices())


class ListPackageVersionSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())
    query_key = serializers.CharField(help_text=_("查询关键字"))


class BulkCreatePackageSerializer(serializers.Serializer):
    packages = serializers.ListSerializer(help_text=_("介质包列表"), child=PackageSerializer(), min_length=1)


class BulkDeletePackageSerializer(serializers.Serializer):
    package_ids = serializers.ListSerializer(help_text=_("介质包ID列表"), child=serializers.IntegerField())
