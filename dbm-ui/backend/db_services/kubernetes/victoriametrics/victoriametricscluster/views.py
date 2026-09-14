# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.resources import serializers
from backend.db_services.kubernetes.victoriametrics import constants
from backend.db_services.kubernetes.victoriametrics.victoriametricscluster import yasg_slz
from backend.db_services.kubernetes.victoriametrics.victoriametricscluster.query import (
    VictoriaMetricsClusterListRetrieveResource,
)
from backend.db_services.kubernetes.victoriametrics.victoriametricscluster.serializers import VMStorageCLBSerializer
from backend.db_services.kubernetes.victoriametrics.views import BaseVictoriaMetricsResourceViewSet
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群列表"),
        query_serializer=serializers.ListResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群详情"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取实例列表"),
        query_serializer=serializers.ListInstancesSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve_instance",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取实例详情"),
        query_serializer=serializers.RetrieveInstancesSerializer(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_table_fields",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取查询返回字段"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceFieldSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="vmstorage_clb",
    decorator=common_swagger_auto_schema(
        operation_summary=_("启用/停用 vmstorage 实例级 CLB 暴露"),
        request_body=VMStorageCLBSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.VMStorageCLBResponseSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
class VictoriaMetricsClusterResourceViewSet(BaseVictoriaMetricsResourceViewSet):
    query_class = VictoriaMetricsClusterListRetrieveResource

    def _get_custom_permissions(self):
        if self.action == "vmstorage_clb":
            return [DBManagePermission(actions=[ActionEnum.K8S_VICTORIAMETRICS_MANAGE])]
        return super()._get_custom_permissions()

    @action(
        methods=["POST"],
        detail=False,
        url_path="vmstorage_clb",
        serializer_class=VMStorageCLBSerializer,
    )
    def vmstorage_clb(self, request, bk_biz_id: int):
        """启用/停用 vmstorage 实例级 CLB 暴露"""
        data = self.params_validate(self.get_serializer_class())
        result = self.query_class.set_vmstorage_clb_enabled(
            bk_biz_id=bk_biz_id,
            cluster_id=data["cluster_id"],
            enable=data["enable"],
            bk_username=request.user.username,
        )
        return Response(result)
