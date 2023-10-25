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
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import (
    PaginatedResponseSwaggerAutoSchema,
    ResponseSwaggerAutoSchema,
    common_swagger_auto_schema,
)
from backend.configuration.constants import BizSettingsEnum
from backend.configuration.models import BizSettings
from backend.db_meta.models import Cluster
from backend.db_services.mysql.open_area.filters import TendbOpenAreaConfigListFilter
from backend.db_services.mysql.open_area.handlers import OpenAreaHandler
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.db_services.mysql.open_area.serializers import (
    TendbOpenAreaConfigSerializer,
    TendbOpenAreaResultPreviewResponseSerializer,
    TendbOpenAreaResultPreviewSerializer,
    VarAlterSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.openarea import OpenareaConfigPermission
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "db_services/openarea"


class OpenAreaViewSet(viewsets.AuditedModelViewSet):
    """开区操作的视图集"""

    queryset = TendbOpenAreaConfig.objects.all()
    serializer_class = TendbOpenAreaConfigSerializer
    pagination_class = AuditedLimitOffsetPagination
    filter_class = TendbOpenAreaConfigListFilter

    def _get_custom_permissions(self):
        if self.action in ["create", "update", "destroy"]:
            return [OpenareaConfigPermission(self.action)]
        return [DBManagePermission()]

    def get_queryset(self):
        # 过滤业务下的集群模板
        bk_biz_id = self.request.parser_context["kwargs"].get("bk_biz_id")
        return self.queryset.filter(bk_biz_id=bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("创建开区模板"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: TendbOpenAreaConfigSerializer(label=_("创建开区模板"))},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("开区模板列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=[
            ActionEnum.TENDBCLUSTER_OPENAREA_CONFIG_UPDATE,
            ActionEnum.TENDBCLUSTER_OPENAREA_CONFIG_DESTROY,
            ActionEnum.MYSQL_OPENAREA_CONFIG_DESTROY,
            ActionEnum.MYSQL_OPENAREA_CONFIG_UPDATE,
        ],
        resource_meta=ResourceEnum.OPENAREA_CONFIG,
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        # 填充集群信息
        source_cluster_ids = [data["source_cluster_id"] for data in resp.data["results"]]
        cluster_id__info = {
            cluster.id: cluster.simple_desc for cluster in Cluster.objects.filter(id__in=source_cluster_ids)
        }
        for data in resp.data["results"]:
            data["source_cluster"] = cluster_id__info[data["source_cluster_id"]]

        return resp

    @common_swagger_auto_schema(
        operation_summary=_("开区模板详情"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: TendbOpenAreaConfigSerializer(label=_("开区模板详情"))},
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        # 补充源集群信息
        resp.data["source_cluster"] = Cluster.objects.get(id=resp.data["source_cluster_id"]).simple_desc
        return resp

    @common_swagger_auto_schema(
        operation_summary=_("更新开区模板"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: TendbOpenAreaConfigSerializer(label=_("更新开区模板"))},
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除开区模板"),
        auto_schema=ResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("获取开区结果预览"),
        request_body=TendbOpenAreaResultPreviewSerializer(),
        responses={status.HTTP_200_OK: TendbOpenAreaResultPreviewResponseSerializer()},
        auto_schema=ResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbOpenAreaResultPreviewSerializer)
    def preview(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        validated_data["operator"] = request.user.username
        return Response(OpenAreaHandler.openarea_result_preview(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("变量表修改"),
        request_body=VarAlterSerializer(),
        auto_schema=ResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=VarAlterSerializer)
    def alter_var(self, request, *args, **kwargs):
        bk_biz_id = kwargs["bk_biz_id"]
        biz_vars: list = BizSettings.get_setting_value(bk_biz_id=bk_biz_id, key=BizSettingsEnum.OPEN_AREA_VARS)
        data = self.params_validate(self.get_serializer_class())

        try:
            # 对变量表进行简单的新增/删除和更新
            if data["op_type"] in ["add", "update"]:
                biz_vars.append(data["new_var"])
            if data["op_type"] in ["delete", "update"]:
                biz_vars.remove(data["old_var"])
        except ValueError:
            # 如果var不存在，remove会触发ValueError，忽略
            pass

        BizSettings.insert_setting_value(
            bk_biz_id=bk_biz_id, key=BizSettingsEnum.OPEN_AREA_VARS, value_type="dict", value=biz_vars
        )
        return Response()
