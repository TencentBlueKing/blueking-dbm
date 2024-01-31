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
from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.enums import AccessLayer, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources import serializers
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import SearchResourceTreeSLZ
from backend.db_services.dbbase.resources.viewsets import ResourceViewSet
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.db_services.mongodb.resources import constants, yasg_slz
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListMongoDBResourceSLZ(),
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
        query_serializer=serializers.MongoDBListInstancesSerializer(),
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
class MongoDBViewSet(ResourceViewSet):
    query_class = MongoDBListRetrieveResource
    query_serializer_class = serializers.ListMongoDBResourceSLZ
    list_instances_slz = serializers.MongoDBListInstancesSerializer

    @common_swagger_auto_schema(
        operation_summary=_("获取实例的角色类型"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=False)
    def get_instance_role(self, request, *args, **kwargs):
        storage_role_types = MachineTypeInstanceRoleMap[MachineType.MONGODB]
        proxy_role_types = [AccessLayer.PROXY]
        return Response([*storage_role_types, *proxy_role_types])


class ResourceTreeViewSet(SystemViewSet):
    serializer_class = SearchResourceTreeSLZ

    @common_swagger_auto_schema(
        operation_summary=_("获取资源拓扑树"),
        query_serializer=SearchResourceTreeSLZ(),
        responses={status.HTTP_200_OK: ResourceTreeSLZ()},
        tags=[constants.RESOURCE_TAG],
    )
    def get_resource_tree(self, request, bk_biz_id):
        cluster_type = self.params_validate(self.get_serializer_class())["cluster_type"]
        clusters = Cluster.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
        )
        return Response(
            [
                {
                    "instance_name": cluster.name,
                    "instance_id": cluster.id,
                    "obj_id": ResourceNodeType.CLUSTER.value,
                    "obj_name": ResourceNodeType.CLUSTER.name,
                    "extra": {
                        "domain": cluster.immute_domain,
                        "version": cluster.major_version,
                    },
                }
                for cluster in clusters
            ]
        )
