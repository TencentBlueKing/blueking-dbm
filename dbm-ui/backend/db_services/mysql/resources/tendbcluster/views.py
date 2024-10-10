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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_services.dbbase.resources import serializers, viewsets
from backend.db_services.mysql.resources import constants
from backend.db_services.mysql.resources.tendbcluster import yasg_slz
from backend.db_services.mysql.resources.tendbcluster.query import ListRetrieveResource
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListTendbClusterResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListInstancesSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedInstanceResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve_instance",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.RetrieveInstancesSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.ResourceInstanceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_machines",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListTendbClusterMachineResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedMachineResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_table_fields",
    decorator=common_swagger_auto_schema(
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_topo_graph",
    decorator=common_swagger_auto_schema(
        responses={status.HTTP_200_OK: yasg_slz.ResourceTopoGraphSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
class SpiderViewSet(viewsets.ResourceViewSet):
    """Spider 架构资源"""

    query_class = ListRetrieveResource
    query_serializer_class = serializers.ListTendbClusterResourceSLZ
    list_machine_slz = serializers.ListTendbClusterMachineResourceSLZ
    db_type = DBType.TenDBCluster

    list_perm_actions = [
        ActionEnum.TENDBCLUSTER_VIEW,
        ActionEnum.TENDBCLUSTER_SPIDER_SLAVE_DESTROY,
        ActionEnum.TENDBCLUSTER_ENABLE_DISABLE,
        ActionEnum.TENDBCLUSTER_WEBCONSOLE,
        ActionEnum.TENDBCLUSTER_DESTROY,
        ActionEnum.TENDBCLUSTER_SPIDER_ADD_NODES,
        ActionEnum.TENDBCLUSTER_SPIDER_REDUCE_NODES,
        ActionEnum.TENDBCLUSTER_SPIDER_MNT_DESTROY,
        ActionEnum.TENDBCLUSTER_NODE_REBALANCE,
        ActionEnum.TENDBCLUSTER_DUMP_DATA,
    ]
    list_instance_perm_actions = [ActionEnum.TENDBCLUSTER_VIEW]
    list_external_perm_actions = [ActionEnum.ACCESS_ENTRY_EDIT]

    @staticmethod
    def _external_perm_param_field(kwargs):
        return {
            ResourceEnum.BUSINESS.id: kwargs["bk_biz_id"],
            ResourceEnum.DBTYPE.id: kwargs["view_class"].db_type.value,
        }

    @action(methods=["POST"], detail=False, url_path="get_cluster_primary")
    def get_cluster_primary(self, request, bk_biz_id: int):
        """获取集群primary"""
        cluster_ids = request.data.get("cluster_ids")
        return Response(self.query_class.get_cluster_primary(cluster_ids))
