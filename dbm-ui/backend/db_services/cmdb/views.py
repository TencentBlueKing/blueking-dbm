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
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.api import db_module
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

from . import biz, serializers

SWAGGER_TAG = "db_services/cmdb"


class CMDBViewSet(viewsets.SystemViewSet):
    lookup_field = "bk_biz_id"

    def _get_custom_permissions(self):
        if self.action in ["list_bizs", "list_modules", "list_cc_obj_user"]:
            return []

        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("业务列表"),
        responses={status.HTTP_200_OK: serializers.BIZSLZ(label=_("业务信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_bizs(self, request):
        serializer = serializers.BIZSLZ(biz.list_bizs(request.user.username), many=True)
        return Response(serializer.data)

    @common_swagger_auto_schema(
        operation_summary=_("业务下的模块列表"),
        query_serializer=serializers.ListModulesSLZ(),
        responses={status.HTTP_200_OK: serializers.ModuleSLZ(label=_("模块信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=serializers.ListModulesSLZ)
    def list_modules(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        cluster_type = validated_data["cluster_type"]
        serializer = serializers.ModuleSLZ(biz.list_modules_by_biz(bk_biz_id, cluster_type), many=True)
        return Response(serializer.data)

    @common_swagger_auto_schema(
        operation_summary=_("创建数据库模块"),
        request_body=serializers.CreateModuleSLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=serializers.CreateModuleSLZ)
    def create_module(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        cluster_type = validated_data["cluster_type"]
        db_module_name = validated_data["db_module_name"]
        return Response(db_module.apis.create(bk_biz_id, db_module_name, cluster_type))

    @common_swagger_auto_schema(
        operation_summary=_("设置业务英文缩写"),
        request_body=serializers.SetBkAppAbbrSLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=serializers.SetBkAppAbbrSLZ)
    def set_db_app_abbr(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        biz.set_db_app_abbr(bk_biz_id, validated_data["db_app_abbr"], raise_exception=True)
        return Response()

    @common_swagger_auto_schema(operation_summary=_("查询 CC 角色对象"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=True)
    def list_cc_obj_user(self, request, bk_biz_id):
        return Response(biz.list_cc_obj_user(bk_biz_id))
