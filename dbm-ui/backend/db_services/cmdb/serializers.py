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

from backend.db_meta.enums import ClusterType, ClusterTypeModuleComponentDefine
from backend.db_services.cmdb.constants import MAX_DB_APP_ABBR_LIMIT, MAX_DB_MODULE_LIMIT
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum


class ListBizWithActionSLZ(serializers.Serializer):
    action = serializers.CharField(help_text=_("查询的权限动作"), required=False)

    def validate(self, attrs):
        if not attrs.get("action"):
            return attrs

        action_instance = ActionEnum.get_action_by_id(attrs["action"])
        related_resource_types = action_instance.related_resource_types
        if len(related_resource_types) != 1 or related_resource_types[0] != ResourceEnum.BUSINESS:
            raise serializers.ValidationError(_("只允许查询关联资源为业务的动作权限"))
        attrs["action"] = action_instance
        return attrs


class BIZSLZ(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    name = serializers.CharField(help_text=_("业务名"))
    english_name = serializers.CharField(help_text=_("业务英文名"))
    permission = serializers.JSONField(help_text=_("业务权限列表"))
    status = serializers.CharField(help_text=_("纳管状态"))
    tags = serializers.ListField(help_text=_("标签列表"), child=serializers.JSONField(), allow_empty=True)
    managed_time = serializers.DateTimeField(help_text=_("纳管时间"))


class ModuleLayerOsSLZ(serializers.Serializer):
    permit_os_type = serializers.CharField(help_text=_("操作系统类型"))
    permit_os = serializers.ListField(
        help_text=_("操作系统范围，空列表表示跟随版本包"),
        child=serializers.CharField(allow_blank=False),
        allow_empty=True,
    )


class ModuleLayerVersionSLZ(ModuleLayerOsSLZ):
    db_version_id = serializers.IntegerField(help_text=_("版本ID"), min_value=1)


class ModuleSLZ(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    name = serializers.CharField(help_text=_("DB模块名"))
    db_version_info = serializers.JSONField(help_text=_("各组件版本与操作系统"), required=False)


class ListModulesSLZ(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class CreateModuleSLZ(serializers.Serializer):
    db_module_name = serializers.CharField(help_text=_("DB模块名"))
    alias_name = serializers.CharField(help_text=_("DB模块别名"), required=False, default="")
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    db_versions = serializers.DictField(
        help_text=_("各组件版本。MySQL 单节点、主从、TenDBCluster 必填"),
        required=False,
    )

    def validate(self, attrs):
        if len(attrs["db_module_name"]) > MAX_DB_MODULE_LIMIT:
            raise serializers.ValidationError(_("请确保模块名称的长度不超过: {}").format(MAX_DB_MODULE_LIMIT))
        if attrs["cluster_type"] in ClusterTypeModuleComponentDefine and "db_versions" not in attrs:
            raise serializers.ValidationError(_("请填写各层版本"))
        if "db_versions" in attrs:
            attrs["db_versions"] = self.clean_component_layers(attrs["db_versions"], ModuleLayerVersionSLZ)
        return attrs

    @classmethod
    def clean_component_layers(cls, raw_versions, layer_serializer):
        """按组件校验 db_versions，错误按组件名汇总后一次返回。"""
        cleaned = {}
        errors = {}
        for key, layer in raw_versions.items():
            serializer = layer_serializer(data=layer)
            if serializer.is_valid():
                cleaned[key] = dict(serializer.validated_data)
            else:
                errors[key] = serializer.errors
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned


class UpdateModuleVersionOsSLZ(serializers.Serializer):
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"), min_value=1)
    db_versions = serializers.DictField(help_text=_("要修改操作系统的组件"), allow_empty=False)

    def validate_db_versions(self, value):
        return CreateModuleSLZ.clean_component_layers(value, ModuleLayerOsSLZ)


class CheckDbModuleUniqueSLZ(serializers.Serializer):
    db_module_name = serializers.CharField(help_text=_("DB模块名"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    def validate(self, attrs):
        if len(attrs["db_module_name"]) > MAX_DB_MODULE_LIMIT:
            raise serializers.ValidationError(_("请确保模块名称的长度不超过: {}").format(MAX_DB_MODULE_LIMIT))

        return attrs


class CheckDbModuleUniqueResponseSLZ(serializers.Serializer):
    is_unique = serializers.BooleanField(help_text=_("是否唯一(同业务+集群类型下不存在同名模块)"))


class SetBkAppAbbrSLZ(serializers.Serializer):
    db_app_abbr = serializers.CharField(help_text=_("英文缩写"))

    def validate(self, attrs):
        if len(attrs["db_app_abbr"]) > MAX_DB_APP_ABBR_LIMIT:
            raise serializers.ValidationError(_("请确保业务CODE的长度不超过: {}").format(MAX_DB_APP_ABBR_LIMIT))

        return attrs


class TopoSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class ListNodesSerializer(TopoSerializer):
    limit = serializers.IntegerField(help_text=_("单页数量"))
    page = serializers.IntegerField(help_text=_("页数"))
    module_id = serializers.IntegerField(help_text=_("模块ID"), required=False)
    set_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
