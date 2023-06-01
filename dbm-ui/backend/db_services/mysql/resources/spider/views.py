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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.resources import constants, serializers, viewsets
from backend.db_services.mysql.resources.spider.query import ListRetrieveResource


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListMySQLResourceSLZ(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListInstancesSerializer(),
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
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_topo_graph",
    decorator=common_swagger_auto_schema(
        tags=[constants.RESOURCE_TAG],
    ),
)
class SpiderViewSet(viewsets.ResourceViewSet):
    """Spider 架构资源"""

    query_class = ListRetrieveResource
    query_serializer_class = serializers.ListMySQLResourceSLZ
