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
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.dbconfig.constants import ConfType, LevelName
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, DBModule
from backend.db_services.dbconfig import serializers
from backend.db_services.dbconfig.dataclass import (
    DBBaseConfig,
    DBConfigDeployData,
    DBConfigLevelData,
    UpsertConfigData,
)
from backend.db_services.dbconfig.handlers import DBConfigHandler
from backend.db_services.dbconfig.serializers import (
    ChangeConfNameSerializer,
    CloneModuleQuerySerializer,
    DeleteConfFileLevelSerializer,
    DeleteModuleConfigSerializer,
    ListConfFilesSerializer,
    ListConfItemChangesSerializer,
    ListConfNameChangesSerializer,
    ListConfTypesSerializer,
    ListCosConfigsSerializer,
    ListLevelValuesSerializer,
    RecoverDefaultConfItemSerializer,
    ValidateConfItemSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.drf_perm.dbconfig import (
    BizDBConfigPermission,
    ClusterLevelConfigPermission,
    GlobalConfigPermission,
    meta_cluster_type_to_db_type,
)
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "config"


def _get_level_config_perm_action(kwargs):
    """get_level_config 编辑权限的动作随 level_name 变化：集群级使用 {dbtype}_dbconfig_edit，其余使用 dbconfig_edit"""
    if kwargs.get("level_name") == LevelName.CLUSTER:
        cluster = Cluster.objects.get(immute_domain=kwargs["level_value"])
        db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        return [getattr(ActionEnum, f"{db_type.upper()}_DBCONFIG_EDIT")]
    return [ActionEnum.DBCONFIG_EDIT]


def _get_level_config_perm_resource(kwargs):
    """get_level_config 编辑权限的资源随 level_name 变化：集群级为集群实例，其余为 dbtype + 业务"""
    if kwargs.get("level_name") == LevelName.CLUSTER:
        cluster = Cluster.objects.get(immute_domain=kwargs["level_value"])
        return cluster.id
    return {
        ResourceEnum.DBTYPE.id: meta_cluster_type_to_db_type(kwargs["meta_cluster_type"]),
        ResourceEnum.BUSINESS.id: kwargs["bk_biz_id"],
    }


class ConfigViewSet(viewsets.SystemViewSet):
    # 层级感知查看：app/module 级用 db_manage，cluster 级用 {dbtype}_view
    LEVEL_VIEW_ACTIONS = ("get_level_config", "list_confitem_changes")
    # 层级感知编辑：app/module 级用 dbconfig_edit，cluster 级用 {dbtype}_dbconfig_edit
    LEVEL_EDIT_ACTIONS = ("upsert_level_config", "recover_default_conf_item")

    action_permission_map = {
        # 业务级查看：复用 db_manage（业务访问）
        (
            "list_biz_configs",
            "list_cluster_module_conf_files",
            "get_common_level_config",
            "list_level_values",
            "list_cos_configs",
            "get_config_version_detail",
        ): [DBManagePermission([ActionEnum.DB_MANAGE])],
        # 业务/模块级编辑：dbconfig_edit（dbtype 由 meta_cluster_type 推导，通用配置用 common 兜底）
        (
            "save_module_deploy_info",
            "delete_module_config",
            "delete_level_value",
            "upsert_common_level_config",
        ): [BizDBConfigPermission([ActionEnum.DBCONFIG_EDIT])],
        (
            "list_platform_configs",
            "get_platform_config",
            "list_confname_changes",
        ): [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])],
        (
            "create_platform_config",
            "upsert_platform_config",
            "change_conf_names",
        ): [GlobalConfigPermission([ActionEnum.GLOBAL_DBCONFIG_EDIT])],
        (
            "get_module_by_id",
            "module_clone_query",
            "list_config_names",
            "check_conf_name_exists",
            "list_conf_name_types",
            "validate_conf_items",
            "list_config_version_history",
            "list_conf_types",
        ): [],
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

    def _get_custom_permissions(self):
        # 层级感知：业务/模块级与集群级使用不同鉴权
        if self.action in [*self.LEVEL_VIEW_ACTIONS, *self.LEVEL_EDIT_ACTIONS]:
            is_edit = self.action in self.LEVEL_EDIT_ACTIONS
            level_name = get_request_key_id(self.request, key="level_name")
            if level_name == LevelName.CLUSTER:
                return [ClusterLevelConfigPermission(is_edit=is_edit)]
            if is_edit:
                return [BizDBConfigPermission([ActionEnum.DBCONFIG_EDIT])]
            else:
                return [DBManagePermission([ActionEnum.DB_MANAGE])]

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
        operation_summary=_("检查配置项是否存在"),
        query_serializer=serializers.ConfNameExistsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ConfNameExistsSerializer)
    def check_conf_name_exists(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(data)
        return Response(
            DBConfigHandler(base_conf).check_conf_name_exists(conf_file=data["conf_file"], conf_name=data["conf_name"])
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询配置值类型与子类型定义"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_conf_name_types(self, request):
        return Response(DBConfigHandler.list_conf_name_types())

    @common_swagger_auto_schema(
        operation_summary=_("配置项定义和值合法性校验"),
        request_body=ValidateConfItemSerializer(many=True),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.ValidateConfItemSerializer)
    def validate_conf_items(self, request):
        slz = ValidateConfItemSerializer(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        return Response(DBConfigHandler.validate_conf_items(slz.validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("修改/新增/删除平台配置项定义"),
        request_body=ChangeConfNameSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ChangeConfNameSerializer)
    def change_conf_names(self, request):
        params = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=params["meta_cluster_type"], conf_type=params["conf_type"])
        return Response(DBConfigHandler(base_conf).change_conf_names(params))

    @common_swagger_auto_schema(
        operation_summary=_("查询平台配置列表"),
        query_serializer=serializers.ListPublicConfigRequestSerializer(),
        responses={status.HTTP_200_OK: serializers.ListPublicConfigResponseSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: meta_cluster_type_to_db_type(d["meta_cluster_type"]),
        actions=[ActionEnum.GLOBAL_DBCONFIG_EDIT],
        resource_meta=ResourceEnum.DBTYPE,
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListPublicConfigRequestSerializer)
    def list_platform_configs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        conf_file = validated_data.get("conf_file", "")
        return Response(DBConfigHandler(base_conf).list_platform_configs(conf_file))

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
    @Permission.decorator_external_permission_field(
        param_field=lambda d: meta_cluster_type_to_db_type(d["meta_cluster_type"]),
        actions=[ActionEnum.GLOBAL_DBCONFIG_EDIT],
        resource_meta=ResourceEnum.DBTYPE,
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
            ResourceEnum.DBTYPE.id: meta_cluster_type_to_db_type(d["meta_cluster_type"]),
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
        conf_file = validated_data.get("conf_file", "")
        return Response(DBConfigHandler(base_conf).list_biz_configs(bk_biz_id=bk_biz_id, conf_file=conf_file))

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
        operation_summary=_("编辑层级（业务、模块、集群）配置"),
        request_body=serializers.UpsertLevelConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.UpsertLevelConfigSerializer)
    def upsert_common_level_config(self, request):
        return self.upsert_level_config(request)

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
    @Permission.decorator_external_permission_field(
        action_filed=_get_level_config_perm_action,
        param_field=_get_level_config_perm_resource,
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.GetLevelConfigDetailSerializer)
    def get_level_config(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(validated_data)
        dbconfig_level_data = DBConfigLevelData.from_dict(validated_data)
        return Response(DBConfigHandler(base_conf, True).get_level_config(dbconfig_level_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询通用层级配置详情"),
        request_body=serializers.GetLevelConfigDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.GetLevelConfigDetailSerializer)
    def get_common_level_config(self, request):
        return self.get_level_config(request)

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
        # 查询模块配置详情
        base_conf = DBBaseConfig.from_dict({"meta_cluster_type": dbmodule_obj.cluster_type, "conf_type": "deploy"})
        deconfig_deploy_data = DBConfigDeployData.from_dict(
            {"bk_biz_id": dbmodule_obj.bk_biz_id, "module_id": module_id}
        )
        data = DBConfigHandler(base_conf).get_module_by_id(deconfig_deploy_data)
        # 更新模块名称信息
        data.update(
            {
                "db_module_id": dbmodule_obj.db_module_id,
                "db_module_name": dbmodule_obj.db_module_name,
                "alias_name": dbmodule_obj.alias_name,
            }
        )
        return Response(data)

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

    @common_swagger_auto_schema(
        operation_summary=_("[平台配置]查询配置项定义的变更历史"),
        query_serializer=ListConfNameChangesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListConfNameChangesSerializer)
    def list_confname_changes(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["namespace"], conf_type=data.get("conf_type", ""))
        return Response(DBConfigHandler(base_conf).list_confname_changes(data))

    @common_swagger_auto_schema(
        operation_summary=_("[业务集群配置]查询配置的变更历史"),
        query_serializer=ListConfItemChangesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListConfItemChangesSerializer)
    def list_confitem_changes(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["namespace"], conf_type=data.get("conf_type", ""))
        return Response(DBConfigHandler(base_conf).list_confitem_changes(data))

    @common_swagger_auto_schema(
        operation_summary=_("查询配置类型列表"),
        query_serializer=ListConfTypesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListConfTypesSerializer)
    def list_conf_types(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type="")
        return Response(DBConfigHandler(base_conf).list_conf_types())

    @common_swagger_auto_schema(
        operation_summary=_("查询集群模块支持的配置文件列表"),
        query_serializer=ListConfFilesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListConfFilesSerializer)
    def list_cluster_module_conf_files(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type="")
        res = DBConfigHandler(base_conf).list_cluster_module_conf_files(
            bk_biz_id=data["bk_biz_id"],
            db_module_id=data.get("db_module_id"),
            cluster_id=data.get("cluster_id"),
            deploy_versions=data.get("deploy_versions"),
        )
        return Response(res)

    @common_swagger_auto_schema(
        operation_summary=_("删除模块配置"),
        request_body=DeleteModuleConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DeleteModuleConfigSerializer)
    def delete_module_config(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type="")
        return Response(DBConfigHandler(base_conf).delete_module_config(data))

    @common_swagger_auto_schema(
        operation_summary=_("恢复默认值"),
        request_body=RecoverDefaultConfItemSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RecoverDefaultConfItemSerializer)
    def recover_default_conf_item(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig.from_dict(data)
        return Response(DBConfigHandler(base_conf).recover_default_conf_item(data))

    @common_swagger_auto_schema(
        operation_summary=_("查询COS配置列表"),
        query_serializer=ListCosConfigsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        actions=[ActionEnum.DBCONFIG_EDIT],
        param_field=lambda d: {
            ResourceEnum.DBTYPE.id: "common",
            ResourceEnum.BUSINESS.id: d["bk_biz_id"],
        },
        resource_meta=[ResourceEnum.DBTYPE, ResourceEnum.BUSINESS],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListCosConfigsSerializer)
    def list_cos_configs(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type="common", conf_type=ConfType.BACKUP_CLIENT)
        return Response(DBConfigHandler(base_conf).list_cos_configs(bk_biz_id=data["bk_biz_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("查询配置文件的级别值列表"),
        query_serializer=ListLevelValuesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListLevelValuesSerializer)
    def list_level_values(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type=data["conf_type"])
        return Response(
            DBConfigHandler(base_conf).list_level_values(
                bk_biz_id=data["bk_biz_id"],
                conf_file=data["conf_file"],
                level_name=data["level_name"],
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("删除某个级别的配置文件"),
        request_body=DeleteConfFileLevelSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DeleteConfFileLevelSerializer)
    def delete_level_value(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type=data["conf_type"])
        return Response(DBConfigHandler(base_conf).delete_level_value(data))

    @common_swagger_auto_schema(
        operation_summary=_("克隆模块配置的查询对比结果"),
        request_body=CloneModuleQuerySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CloneModuleQuerySerializer)
    def module_clone_query(self, request):
        data = self.params_validate(self.get_serializer_class())
        base_conf = DBBaseConfig(meta_cluster_type=data["meta_cluster_type"], conf_type=data["conf_type"])
        return Response(DBConfigHandler(base_conf).module_clone_query(data))
