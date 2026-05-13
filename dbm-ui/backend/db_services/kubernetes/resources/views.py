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

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.resources.views import BaseListResourceViewSet
from backend.db_services.dbbase.resources.viewsets import ResourceViewSet
from backend.db_services.kubernetes.resources import constants
from backend.db_services.kubernetes.resources.query import KubernetesBaseListRetrieveResource
from backend.db_services.kubernetes.resources.serializers import (
    ClusterOperationLogSerializer,
    KubernetesComponentSpecSerializer,
    KubernetesRetrieveInstancesSerializer,
    KubernetesTopoGraphSerializer,
)


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class ListResourceViewSet(BaseListResourceViewSet):
    pass


class KubernetesResourceViewSet(ResourceViewSet):
    query_class = KubernetesBaseListRetrieveResource
    retrieve_instances_slz = KubernetesRetrieveInstancesSerializer

    @action(methods=["GET"], detail=False, url_path="retrieve_instance")
    def retrieve_instance(self, request, bk_biz_id: int):
        """查询实例详情"""
        query_params = self.params_validate(self.retrieve_instances_slz)
        return Response(self.query_class.retrieve_ins(query_params))

    @common_swagger_auto_schema(
        operation_summary=_("获取集群操作记录"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(
        methods=["GET"], detail=False, url_path="get_operation_log", serializer_class=ClusterOperationLogSerializer
    )
    def get_operation_log(self, request, *args, **kwargs):
        """获取集群操作日志"""
        data = self.params_validate(self.get_serializer_class())
        data = self.paginator.paginate_list(request, data["bk_biz_id"], self.query_class.get_operation_log, data)
        return self.get_paginated_response(data)

    @common_swagger_auto_schema(
        operation_summary=_("获取集群拓扑"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_topo_graph", serializer_class=KubernetesTopoGraphSerializer)
    def get_topo_graph(self, request, bk_biz_id: int, cluster_id: int):
        """获取拓扑图"""
        data = self.params_validate(self.get_serializer_class())
        return Response(
            self.query_class.get_topo_graph(bk_biz_id, cluster_id, data["k8sClusterName"], data["namespace"])
        )

    @common_swagger_auto_schema(
        operation_summary=_("获取集群组件规格"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="get_component_spec",
        serializer_class=KubernetesComponentSpecSerializer,
    )
    def get_component_spec(self, request, *args, **kwargs):
        """获取集群组件规格"""
        data = self.params_validate(self.get_serializer_class())
        data["bk_username"] = request.user.username
        return Response(self.query_class.get_component_spec(data))
