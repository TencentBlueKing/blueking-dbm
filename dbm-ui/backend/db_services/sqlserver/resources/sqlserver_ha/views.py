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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_services.dbbase.resources import serializers, viewsets
from backend.db_services.sqlserver.resources import constants
from backend.db_services.sqlserver.resources.sqlserver_ha import yasg_slz
from backend.db_services.sqlserver.resources.sqlserver_ha.query import ListRetrieveResource
from backend.iam_app.dataclass.actions import ActionEnum


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListSQLServerResourceSLZ(),
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
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve_instance",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.RetrieveInstancesSerializer(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_machines",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListMachineSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedMachineResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_table_fields",
    decorator=common_swagger_auto_schema(
        responses={status.HTTP_200_OK: yasg_slz.ResourceFieldSLZ()},
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
class SQLServerHaViewSet(viewsets.ResourceViewSet):
    """SQLServer Ha 架构资源"""

    query_class = ListRetrieveResource
    query_serializer_class = serializers.ListSQLServerResourceSLZ
    db_type = DBType.Sqlserver

    list_perm_actions = [ActionEnum.SQLSERVER_VIEW]
    list_instance_perm_actions = [ActionEnum.SQLSERVER_VIEW]
