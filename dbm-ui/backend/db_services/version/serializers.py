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
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import DBVersion, Distribution, VersionSeries
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.db_package.serializers import PackageSerializer
from backend.db_services.version.constants import SqlserverVersion
from backend.db_services.version.utils import pad_full_version, strip_full_version


class ListVersionSerializer(serializers.Serializer):
    query_key = serializers.ChoiceField(
        help_text=_("查询关键字"), choices=ClusterType.get_choices() + PackageType.get_choices()
    )


class ListSQLServerSystemVersionSerializer(serializers.Serializer):
    sqlserver_version = serializers.ChoiceField(help_text=_("数据库版本"), choices=SqlserverVersion.get_choices())


class DistributionSerializer(AuditedSerializer, serializers.ModelSerializer):
    version_series_count = serializers.IntegerField(read_only=True, help_text=_("关联的版本系列总数"))
    dbversion_count = serializers.IntegerField(read_only=True, help_text=_("关联的介质版本总数"))

    class Meta:
        model = Distribution
        fields = "__all__"

    def validate(self, attrs):
        """
        校验同一 (db_type, pkg_type, name) 组合唯一
        - create: 校验整个表是否已存在
        - partial_update: 用 instance 缺省值兜底, 并排除 self
        """
        attrs = super().validate(attrs)

        instance = self.instance
        db_type = attrs.get("db_type") or (instance and instance.db_type)
        pkg_type = attrs.get("pkg_type") or (instance and instance.pkg_type)
        name = attrs.get("name") if "name" in attrs else (instance and instance.name)

        if not (db_type and pkg_type and name):
            return attrs

        qs = Distribution.objects.filter(db_type=db_type, pkg_type=pkg_type, name=name)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(_("同一介质类型下，发行版名称 [{name}] 已存在").format(name=name))

        return attrs


class VersionSeriesSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = VersionSeries
        fields = "__all__"


class VersionSeriesDeleteSerializer(serializers.Serializer):
    distribution = serializers.IntegerField(help_text=_("发行版ID"), required=True)


class DBVersionConflictCheckSerializer(serializers.Serializer):
    """
    介质版本冲突校验入参:
    - 通过 version_series 反查 distribution, 在 distribution 维度判断 name / full_version 是否冲突
    - exclude_id 用于编辑场景排除自身
    """

    version_series = serializers.IntegerField(help_text=_("版本系列ID"), required=True)
    name = serializers.CharField(help_text=_("版本名称"), required=False, allow_blank=True, default="")
    full_version = serializers.CharField(help_text=_("完整版本号(对外段数)"), required=False, allow_blank=True, default="")
    exclude_id = serializers.IntegerField(help_text=_("排除的介质版本ID, 编辑场景使用"), required=False)


class DBVersionConflictCheckResponseSerializer(serializers.Serializer):
    """介质版本冲突校验出参(用于 swagger 文档)"""

    name_conflict = serializers.BooleanField(help_text=_("版本名称是否冲突"))
    full_version_conflict = serializers.BooleanField(help_text=_("完整版本号是否冲突"))


class DBVersionSerializer(AuditedSerializer, serializers.ModelSerializer):
    packages = serializers.SerializerMethodField(read_only=True, help_text=_("关联的介质列表"))

    class Meta:
        model = DBVersion
        fields = "__all__"
        # 这两个字段由 DBVersion.save() 根据 version_series 自动派生, 不允许前端写入
        read_only_fields = ["distribution_id", "distribution_snapshot"]

    def get_packages(self, obj):
        """获取关联的介质列表"""
        # 使用 prefetch_related 预加载的 package_set，转换为列表避免 QuerySet 问题
        packages = list(obj.package_set.all())

        # 批量查询所有 Package 的 instances，避免 N+1 查询
        if packages:
            package_ids = [pkg.id for pkg in packages]
            package_stats = (
                Package.objects.filter(id__in=package_ids)
                .annotate(instances=Count("storageinstance", distinct=True) + Count("proxyinstance", distinct=True))
                .values("id", "instances")
            )
            instances_map = {item["id"]: item["instances"] for item in package_stats}
        else:
            instances_map = {}

        # 将 instances_map 传递给序列化器 context，避免重复查询
        return PackageSerializer(packages, many=True, context={**self.context, "instances_map": instances_map}).data

    def to_internal_value(self, data):
        """前端按 pkg_type 段数传 full_version, 这里统一补齐到底层 6 段后再交给 model 层"""
        ret = super().to_internal_value(data)
        full_version = ret.get("full_version")
        if not full_version:
            return ret

        ret["full_version"] = pad_full_version(full_version)
        return ret

    def to_representation(self, instance):
        """对外返回 full_version 时按 pkg_type 截掉填充段, 与前端展示对齐"""
        ret = super().to_representation(instance)
        full_version = ret.get("full_version")
        if not full_version:
            return ret

        pkg_type = instance.distribution_snapshot["pkg_type"]
        ret["full_version"] = strip_full_version(full_version, pkg_type)
        return ret
