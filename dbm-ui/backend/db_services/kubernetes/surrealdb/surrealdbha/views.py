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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_services.dbbase.resources import serializers
from backend.db_services.kubernetes.resources.views import KubernetesResourceViewSet
from backend.db_services.kubernetes.surrealdb import constants
from backend.db_services.kubernetes.surrealdb.surrealdbha import yasg_slz
from backend.db_services.kubernetes.surrealdb.surrealdbha.query import SurrealDBHaListRetrieveResource
from backend.iam_app.dataclass.actions import ActionEnum


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
class SurrealDBHaResourceViewSet(KubernetesResourceViewSet):
    query_class = SurrealDBHaListRetrieveResource
    query_serializer_class = serializers.ListKubernetesResourceSLZ
    db_type = DBType.K8sSurrealdb

    list_perm_actions = [
        ActionEnum.K8S_SURREAL_APPLY,
        ActionEnum.K8S_SURREAL_MODIFY,
        ActionEnum.K8S_SURREAL_DESTROY,
        ActionEnum.K8S_SURREAL_START,
        ActionEnum.K8S_SURREAL_STOP,
        ActionEnum.K8S_SURREAL_RESTART,
        ActionEnum.K8S_SURREAL_POD_DELETE,
        ActionEnum.K8S_SURREAL_SCALE,
    ]
