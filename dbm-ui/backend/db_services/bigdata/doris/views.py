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
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_services.bigdata.doris.query import DorisListRetrieveResource
from backend.db_services.bigdata.es import constants
from backend.db_services.bigdata.resources import serializers as bigdata_serializers
from backend.db_services.bigdata.resources import yasg_slz
from backend.db_services.bigdata.resources.views import BigdataResourceViewSet
from backend.db_services.dbbase.resources import serializers
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
@method_decorator(
    name="get_nodes",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群节点"),
        query_serializer=serializers.ListNodesSLZ(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_upgradable_versions",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取Doris集群可升级版本列表"),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_clusters_master",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取Doris集群Master节点"),
        request_body=bigdata_serializers.GetClustersMasterSLZ(),
        tags=[constants.RESOURCE_TAG],
    ),
)
class DorisClusterViewSetBigdata(BigdataResourceViewSet):
    query_class = DorisListRetrieveResource
    query_serializer_class = serializers.ListResourceSLZ
    db_type = DBType.Doris

    list_perm_actions = [
        ActionEnum.DORIS_MANAGE,
        ActionEnum.DORIS_VIEW,
        ActionEnum.DORIS_EDIT,
        ActionEnum.DORIS_DBCONFIG_EDIT,
        ActionEnum.DORIS_DESTROY,
        ActionEnum.DORIS_ENABLE_DISABLE,
        ActionEnum.DORIS_SUBSCRIBE_MONITOR,
        ActionEnum.DORIS_ACCESS_ENTRY_VIEW,
    ]

    @action(methods=["GET"], detail=True, url_path="get_nodes", serializer_class=serializers.ListNodesSLZ)
    def get_nodes(self, request, bk_biz_id: int, cluster_id: int):
        """获取特定角色的节点"""
        params = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.get_nodes(bk_biz_id, cluster_id, params["role"], params.get("keyword")))

    @action(
        methods=["POST"],
        detail=False,
        url_path="get_clusters_master",
        serializer_class=bigdata_serializers.GetClustersMasterSLZ,
    )
    def get_clusters_master(self, request, bk_biz_id: int):
        """获取 Doris 集群 Master 节点"""
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.get_clusters_master(bk_biz_id, validated_data["cluster_ids"]))

    @action(methods=["GET"], detail=True, url_path="get_cold_resource")
    def get_cold_resource(self, request, bk_biz_id: int, cluster_id: int):
        """获取 Doris 集群绑定的独立存储资源"""
        return Response(self.query_class.get_cold_resource(bk_biz_id, cluster_id))

    @action(methods=["GET"], detail=True, url_path="list_upgradable_versions")
    def list_upgradable_versions(self, request, bk_biz_id: int, cluster_id: int):
        """获取 Doris 集群可升级到的版本列表"""
        return Response(self.query_class.list_upgradable_versions(bk_biz_id, cluster_id))
