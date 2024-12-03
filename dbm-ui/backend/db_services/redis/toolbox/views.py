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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.cluster.views import ClusterViewSet as BaseClusterViewSet
from backend.db_services.mysql.cluster.serializers import (
    GetMachineInstancePairResponseSerializer,
    GetMachineInstancePairSerializer,
)
from backend.db_services.redis.constants import RedisVersionQueryType
from backend.db_services.redis.toolbox.handlers import ToolboxHandler
from backend.db_services.redis.toolbox.serializers import (
    GetClusterCapacityInfoSerializer,
    GetClusterModuleInfoSerializer,
    GetClusterVersionSerializer,
    QueryByOneClusterSerializer,
    QueryClusterIpsSerializer,
)
from backend.flow.utils.redis.redis_proxy_util import get_cluster_capacity_update_required_info
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/redis/toolbox"


class ToolboxViewSet(BaseClusterViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("根据IP/实例查询关联对"),
        request_body=GetMachineInstancePairSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetMachineInstancePairResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetMachineInstancePairSerializer)
    def query_machine_instance_pair(self, request, bk_biz_id, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).query_machine_instance_pair(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询集群下的主机列表"),
        query_serializer=QueryClusterIpsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryClusterIpsSerializer, pagination_class=None)
    def query_cluster_ips(self, request, bk_biz_id):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        return Response(ToolboxHandler(bk_biz_id).query_cluster_ips(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("根据cluster_id查询主从关系对"),
        request_body=QueryByOneClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryByOneClusterSerializer)
    def query_master_slave_pairs(self, request, bk_biz_id, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).query_master_slave_pairs(validated_data["cluster_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("查询集群版本信息"),
        query_serializer=GetClusterVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetClusterVersionSerializer, pagination_class=None)
    def get_cluster_versions(self, request, bk_biz_id, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, node_type = data["cluster_id"], data["node_type"]
        if data["type"] == RedisVersionQueryType.ONLINE.value:
            return Response(ToolboxHandler.get_online_cluster_versions(cluster_id, node_type))
        else:
            return Response(ToolboxHandler.get_update_cluster_versions(cluster_id, node_type))

    @common_swagger_auto_schema(
        operation_summary=_("获取集群容量变更所需信息"),
        query_serializer=GetClusterCapacityInfoSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetClusterCapacityInfoSerializer, pagination_class=None)
    def get_cluster_capacity_update_info(self, request, bk_biz_id, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        update_info = get_cluster_capacity_update_required_info(**data)
        update_fields = [
            "capacity_update_type",
            "require_spec_id",
            "require_machine_group_num",
            "err_msg",
            "old_machine_info",
        ]
        return Response(dict(zip(update_fields, update_info)))

    @common_swagger_auto_schema(
        operation_summary=_("获取集群module信息"),
        query_serializer=GetClusterModuleInfoSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetClusterModuleInfoSerializer, pagination_class=None)
    def get_cluster_module_info(self, request, bk_biz_id, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, version = data["cluster_id"], data["version"]
        return Response(ToolboxHandler.get_cluster_module_info(cluster_id, version))
