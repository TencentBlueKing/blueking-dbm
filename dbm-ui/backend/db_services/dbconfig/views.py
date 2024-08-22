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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import DBModule
from backend.db_services.dbconfig import serializers
from backend.db_services.dbconfig.dataclass import (
    DBBaseConfig,
    DBConfigDeployData,
    DBConfigLevelData,
    UpsertConfigData,
)
from backend.db_services.dbconfig.handlers import DBConfigHandler
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.iam_app.handlers.drf_perm.dbconfig import BizDBConfigPermission, GlobalConfigPermission
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "config"


class ConfigViewSet(viewsets.SystemViewSet):
    action_permission_map = {
        (
            "list_biz_configs",
            "get_level_config",
            "get_config_version_detail",
        ): [BizDBConfigPermission([ActionEnum.DBCONFIG_VIEW])],
        (
            "upsert_level_config",
            "save_module_deploy_info",
        ): [BizDBConfigPermission([ActionEnum.DBCONFIG_EDIT])],
        (
            "list_platform_configs",
            "get_platform_config",
        ): [GlobalConfigPermission([ActionEnum.GLOBAL_DBCONFIG_VIEW])],
        ("create_platform_config",): [GlobalConfigPermission([ActionEnum.GLOBAL_DBCONFIG_CREATE])],
        ("upsert_platform_config",): [GlobalConfigPermission([ActionEnum.GLOBAL_DBCONFIG_EDIT])],
        ("list_config_names",): [],
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

    def _get_custom_permissions(self):
        # list_config_version_history需要根据业务ID来判断是业务配置还是平台配置
        if self.action == "list_config_version_history":
            if int(self.request.query_params.get("bk_biz_id", 0)):
                return [BizDBConfigPermission([ActionEnum.DBCONFIG_VIEW])]
            else:
                return [GlobalConfigPermission([ActionEnum.GLOBAL_DBCONFIG_VIEW])]
        return super()._get_custom_permissions()

    @common_swagger_auto_schema(
        operation_summary=_("查询配置项名称列表"),
        query_serializer=serializers.GetPublicConfigDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.GetPublicConfigDetailSerializer)
    def list_config_names(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        version = validated_data["version"]
        return Response(DBConfigHandler(base_conf).list_config_names(version))

    @common_swagger_auto_schema(
        operation_summary=_("查询平台配置列表"),
        query_serializer=serializers.ListPublicConfigRequestSerializer(),
        responses={status.HTTP_200_OK: serializers.ListPublicConfigResponseSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: ClusterType.cluster_type_to_db_type(d["meta_cluster_type"]),
        actions=[ActionEnum.GLOBAL_DBCONFIG_EDIT],
        resource_meta=ResourceEnum.DBTYPE,
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListPublicConfigRequestSerializer)
    def list_platform_configs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).list_platform_configs())

    @common_swagger_auto_schema(
        operation_summary=_("新建平台配置"),
        request_body=serializers.CreatePublicConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.CreatePublicConfigSerializer)
    def create_platform_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        name = validated_data["name"]
        version = validated_data["version"]
        upsert_config_data = UpsertConfigData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).create_platform_config(name, version, upsert_config_data))

    @common_swagger_auto_schema(
        operation_summary=_("编辑平台配置"),
        request_body=serializers.CreatePublicConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.CreatePublicConfigSerializer)
    def upsert_platform_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        name = validated_data["name"]
        version = validated_data["version"]
        upsert_config_data = UpsertConfigData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).upsert_platform_config(name, version, upsert_config_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询平台配置详情"),
        query_serializer=serializers.GetPublicConfigDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.GetPublicConfigDetailSerializer)
    def get_platform_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        version = validated_data["version"]
        return Response(DBConfigHandler(base_conf, True).get_platform_config(version))

    @common_swagger_auto_schema(
        operation_summary=_("查询业务配置列表"),
        query_serializer=serializers.ListBizConfigRequestSerializer(),
        responses={status.HTTP_200_OK: serializers.ListPublicConfigResponseSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: {
            ResourceEnum.DBTYPE.id: ClusterType.cluster_type_to_db_type(d["meta_cluster_type"]),
            ResourceEnum.BUSINESS.id: d["bk_biz_id"],
        },
        actions=[ActionEnum.DBCONFIG_EDIT],
        resource_meta=[ResourceEnum.DBTYPE, ResourceEnum.BUSINESS],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListBizConfigRequestSerializer)
    def list_biz_configs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        bk_biz_id = validated_data["bk_biz_id"]
        return Response(DBConfigHandler(base_conf).list_biz_configs(bk_biz_id=bk_biz_id))

    @common_swagger_auto_schema(
        operation_summary=_("编辑层级（业务、模块、集群）配置"),
        request_body=serializers.UpsertLevelConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.UpsertLevelConfigSerializer)
    def upsert_level_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        upsert_config_data = UpsertConfigData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).upsert_level_config(dbconfig_level_data, upsert_config_data))

    @common_swagger_auto_schema(
        operation_summary=_("保存模块部署配置"),
        request_body=serializers.SaveModuleDeployInfoSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.SaveModuleDeployInfoSerializer)
    def save_module_deploy_info(self, request):
        """
        保存模块部署配置，这类配置往往是不可变的，如charset、storage_engine，这里独立提供一个接口进行处理
        """
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        upsert_config_data = UpsertConfigData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).save_module_deploy_info(dbconfig_level_data, upsert_config_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询层级（业务、模块、集群）配置详情"),
        request_body=serializers.GetLevelConfigDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.GetLevelConfigDetailSerializer)
    def get_level_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf, True).get_level_config(dbconfig_level_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询模块配置详情"),
        request_body=serializers.ModuleConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.ModuleConfigSerializer)
    def get_module_by_id(self, request):
        """
        通过module id获取模块配置详情
        """
        validated_data = self.params_validate(self.get_serializer_class())
        module_id = validated_data["module_id"]
        try:
            dbmodule_obj = DBModule.objects.get(db_module_id=module_id)
        except DBModule.DoesNotExist:
            raise Exception("DBModule {} does not exist".format(module_id))
        base_conf = DBBaseConfig.from_dict({"meta_cluster_type": dbmodule_obj.cluster_type, "conf_type": "deploy"})
        deconfig_deploy_data = DBConfigDeployData.from_dict(
            {"bk_biz_id": dbmodule_obj.bk_biz_id, "module_id": module_id}
        )
        return Response(DBConfigHandler(base_conf).get_module_by_id(deconfig_deploy_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询配置发布历史记录"),
        query_serializer=serializers.CommonLevelConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.CommonLevelConfigSerializer)
    def list_config_version_history(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf).list_config_version_history(dbconfig_level_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询配置发布记录详情"),
        query_serializer=serializers.GetConfigVersionDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.GetConfigVersionDetailSerializer)
    def get_config_version_detail(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        revision = validated_data["revision"]
        return Response(DBConfigHandler(base_conf).get_config_version_detail(dbconfig_level_data, revision))
