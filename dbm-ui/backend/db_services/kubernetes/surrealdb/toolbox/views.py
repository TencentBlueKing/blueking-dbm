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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.kubernetes.client import KubernetesApi
from backend.db_services.kubernetes.surrealdb.toolbox.serializers import (
    GetAddonSpecPlanSerializer,
    GetAddonVersionsSerializer,
    GetK8sClusterConfigSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


SWAGGER_TAG = "db_services/surrealdb/toolbox"


class ToolboxViewSet(viewsets.SystemViewSet):
    """工具箱视图集

    Args:
        viewsets (_type_): _description_

    Returns:
        _type_: _description_
    """

    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取存储版本信息"),
        query_serializer=GetAddonVersionsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetAddonVersionsSerializer)
    def get_addon_versions(self, request, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(KubernetesApi.addon_versions(params=validated_data, use_admin=True))

    @common_swagger_auto_schema(
        operation_summary=_("查询BCS集群信息"),
        query_serializer=GetK8sClusterConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetK8sClusterConfigSerializer)
    def get_k8s_cluster_config(self, request, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(KubernetesApi.bcs_regions(params=validated_data, use_admin=True))

    @common_swagger_auto_schema(
        operation_summary=_("查询集群部署套餐"),
        query_serializer=GetAddonSpecPlanSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetAddonSpecPlanSerializer)
    def get_addon_spec_plan(self, request, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(KubernetesApi.addon_spec_plan(params=validated_data, use_admin=True))
