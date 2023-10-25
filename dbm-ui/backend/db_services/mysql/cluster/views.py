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

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import InstanceInnerRole
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.cluster.serializers import (
    FindRelatedClustersByClusterIdRequestSerializer,
    FindRelatedClustersByClusterIdResponseSerializer,
    FindRelatedClustersByInstancesRequestSerializer,
    FindRelatedClustersByInstancesResponseSerializer,
    GetIntersectedSlavaMachinesResponseSerializer,
    GetIntersectedSlavaMachinesSerializer,
    GetTendbMachineInstancePairResponseSerializer,
    GetTendbMachineInstancePairSerializer,
    GetTendbRemoteMachinesResponseSerializer,
    GetTendbRemoteMachinesSerializer,
    GetTendbRemotePairsResponseSerializer,
    GetTendbRemotePairsSerializer,
    QueryClustersRequestSerializer,
    QueryClustersResponseSerializer,
)
from backend.db_services.mysql.dataclass import ClusterFilter, DBInstance
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/mysql/cluster"


class ClusterViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("通过集群查询同机关联集群"),
        request_body=FindRelatedClustersByClusterIdRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: FindRelatedClustersByClusterIdResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=FindRelatedClustersByClusterIdRequestSerializer)
    def find_related_clusters_by_cluster_ids(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ClusterServiceHandler(bk_biz_id).find_related_clusters_by_cluster_ids(validated_data["cluster_ids"])
        )

    @common_swagger_auto_schema(
        operation_summary=_("通过实例查询同机关联集群"),
        request_body=FindRelatedClustersByInstancesRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: FindRelatedClustersByInstancesResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=FindRelatedClustersByInstancesRequestSerializer)
    def find_related_clusters_by_instances(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ClusterServiceHandler(bk_biz_id).find_related_clusters_by_instances(
                [DBInstance(**data) for data in validated_data["instances"]]
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("通过过滤条件批量查询集群"),
        request_body=QueryClustersRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryClustersResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryClustersRequestSerializer)
    def query_clusters(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ClusterServiceHandler(bk_biz_id).query_clusters(
                [ClusterFilter.from_dict(filter_dict) for filter_dict in validated_data["cluster_filters"]]
            )
        )

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

    @common_swagger_auto_schema(
        operation_summary=_("查询tendbcluster集群的remote相关角色机器"),
        request_body=GetTendbRemoteMachinesSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetTendbRemoteMachinesResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetTendbRemoteMachinesSerializer)
    def get_remote_machine_pairs(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ClusterServiceHandler(bk_biz_id).get_remote_machine_pairs(cluster_ids=validated_data["cluster_ids"])
        )

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
        request_body=GetTendbMachineInstancePairSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetTendbMachineInstancePairResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetTendbMachineInstancePairSerializer)
    def get_remote_machine_instance_pair(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).get_remote_machine_instance_pair(validated_data))
