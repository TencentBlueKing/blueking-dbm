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
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.bigdata.influxdb import constants
from backend.db_services.bigdata.influxdb.query import InfluxDBListRetrieveResource
from backend.db_services.bigdata.influxdb.serializers import ListInfluxDBInstancesSerializer
from backend.db_services.bigdata.resources import yasg_slz
from backend.db_services.bigdata.resources.views import BigdataResourceViewSet
from backend.db_services.dbbase.resources import serializers
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import InstanceDetailPermission
from backend.iam_app.handlers.permission import Permission


@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取实例列表"),
        query_serializer=ListInfluxDBInstancesSerializer(),
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
class InfluxDBClusterViewSetBigdata(BigdataResourceViewSet):
    query_class = InfluxDBListRetrieveResource
    query_serializer_class = serializers.ListResourceSLZ

    def list(self, request, bk_biz_id: int, *args, **kwargs):
        """influxdb没有集群，不实现list方法"""
        raise NotImplementedError()

    def list_nodes(self, request, bk_biz_id: int, cluster_id: int):
        """influxdb没有节点，不实现list_nodes"""
        raise NotImplementedError()

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.INFLUXDB.id),
        resource_meta=ResourceEnum.INFLUXDB,
    )
    @action(methods=["GET"], detail=False, url_path="list_instances")
    def list_instances(self, request, bk_biz_id: int, *args, **kwargs):
        query_params = self.params_validate(self.list_instances_slz)
        data = self.paginator.paginate_list(request, bk_biz_id, self.query_class.list_instances, query_params)
        return self.get_paginated_response(data)

    def _get_custom_permissions(self):
        if self.detail or self.action == "retrieve_instance":
            return [InstanceDetailPermission()]
        return [DBManagePermission()]
