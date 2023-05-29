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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.bigdata.es import constants
from backend.db_services.bigdata.es.query import ESListRetrieveResource
from backend.db_services.bigdata.resources import yasg_slz
from backend.db_services.bigdata.resources.views import ResourceViewSet
from backend.db_services.dbbase.resources import serializers


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
    name="get_topo_graph",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群拓扑"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceTopoGraphSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_nodes",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群节点"),
        query_serializer=serializers.ListNodesSLZ(),
        tags=[constants.RESOURCE_TAG],
    ),
)
class EsClusterViewSet(ResourceViewSet):
    query_class = ESListRetrieveResource
    query_serializer_class = serializers.ListResourceSLZ

    @action(methods=["GET"], detail=True, url_path="get_nodes", serializer_class=serializers.ListNodesSLZ)
    def get_nodes(self, request, bk_biz_id: int, cluster_id: int):
        """获取特定角色的节点"""
        params = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.get_nodes(bk_biz_id, cluster_id, params["role"], params.get("keyword")))
