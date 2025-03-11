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
from backend.db_meta.enums import InstanceInnerRole
from backend.db_services.dbbase.cluster.views import ClusterViewSet as BaseClusterViewSet
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.cluster.serializers import (
    GetIntersectedSlavaMachinesResponseSerializer,
    GetIntersectedSlavaMachinesSerializer,
    GetMachineInstancePairResponseSerializer,
    GetMachineInstancePairSerializer,
    GetTendbRemotePairsResponseSerializer,
    GetTendbRemotePairsSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/mysql/cluster"


class ClusterViewSet(BaseClusterViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询tendbcluster集群的remote_db/remote_dr"),
        request_body=GetTendbRemotePairsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetTendbRemotePairsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetTendbRemotePairsSerializer)
    def get_remote_pairs(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).get_remote_pairs(cluster_ids=validated_data["cluster_ids"]))

    @common_swagger_auto_schema(
        operation_summary=_("[tendbcluster]根据实例/机器查询关联对"),
        request_body=GetMachineInstancePairSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetMachineInstancePairResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetMachineInstancePairSerializer)
    def get_remote_machine_instance_pair(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).query_machine_instance_pair(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取关联集群从库的交集"),
        request_body=GetIntersectedSlavaMachinesSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetIntersectedSlavaMachinesResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetIntersectedSlavaMachinesSerializer)
    def get_intersected_slave_machines_from_clusters(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ClusterServiceHandler(bk_biz_id).get_intersected_machines_from_clusters(
                cluster_ids=validated_data["cluster_ids"],
                role=InstanceInnerRole.SLAVE.value,
                is_stand_by=validated_data["is_stand_by"],
            )
        )
