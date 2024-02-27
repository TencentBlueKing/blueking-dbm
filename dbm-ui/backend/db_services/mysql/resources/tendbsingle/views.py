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
from backend.db_services.dbbase.resources import constants, serializers, viewsets
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.permission import Permission

from . import yasg_slz
from .query import ListRetrieveResource


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListMySQLResourceSLZ(),
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
class DBSingleViewSet(viewsets.ResourceViewSet):
    """查询单点部署资源"""

    db_type = DBType.MySQL
    query_class = ListRetrieveResource
    query_serializer_class = serializers.ListMySQLResourceSLZ

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=[
            ActionEnum.MYSQL_AUTHORIZE_RULES,
            ActionEnum.MYSQL_ENABLE_DISABLE,
            ActionEnum.MYSQL_DESTROY,
            ActionEnum.MYSQL_VIEW,
        ],
        resource_meta=ResourceEnum.MYSQL,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["view_class"].db_type,
        actions=[ActionEnum.ACCESS_ENTRY_EDIT],
        resource_meta=ResourceEnum.DBTYPE,
    )
    def list(self, request, bk_biz_id: int):
        return super().list(request, bk_biz_id)
