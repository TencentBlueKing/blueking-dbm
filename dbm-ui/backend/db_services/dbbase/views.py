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
from collections import defaultdict
from typing import Dict, List, Set, Union

from django.db.models import Q
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import ResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.db_meta.models import Cluster, DBModule, ProxyInstance, StorageInstance
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.dbbase.cluster.serializers import CheckClusterDbsResponseSerializer, CheckClusterDbsSerializer
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.dbbase.instances.yasg_slz import CheckInstancesResSLZ, CheckInstancesSLZ
from backend.db_services.dbbase.resources import register
from backend.db_services.dbbase.resources.query import ListRetrieveResource, ResourceList
from backend.db_services.dbbase.serializers import (
    ClusterFilterSerializer,
    CommonQueryClusterResponseSerializer,
    CommonQueryClusterSerializer,
    IsClusterDuplicatedResponseSerializer,
    IsClusterDuplicatedSerializer,
    QueryAllTypeClusterResponseSerializer,
    QueryAllTypeClusterSerializer,
    QueryBizClusterAttrsResponseSerializer,
    QueryBizClusterAttrsSerializer,
)
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper

SWAGGER_TAG = _("集群通用接口")


class DBBaseViewSet(viewsets.SystemViewSet):
    """
    集群通用接口，用于查询/操作集群公共的属性
    """

    pagination_class = AuditedLimitOffsetPagination

    @common_swagger_auto_schema(
        operation_summary=_("查询集群名字是否重复"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=IsClusterDuplicatedSerializer(),
        responses={status.HTTP_200_OK: IsClusterDuplicatedResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=IsClusterDuplicatedSerializer)
    def verify_duplicated_cluster_name(self, request, *args, **kwargs):
        validate_data = self.params_validate(self.get_serializer_class())
        is_duplicated = Cluster.objects.filter(**validate_data).exists()
        return Response(is_duplicated)

    @common_swagger_auto_schema(
        operation_summary=_("查询全集群简略信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=QueryAllTypeClusterSerializer(),
        responses={status.HTTP_200_OK: QueryAllTypeClusterResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryAllTypeClusterSerializer)
    def simple_query_cluster(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        conditions = self.get_serializer().get_conditions(data)
        cluster_queryset = Cluster.objects.filter(**conditions)
        cluster_infos = [cluster.simple_desc for cluster in cluster_queryset]
        return Response(cluster_infos)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群通用信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=CommonQueryClusterSerializer(),
        responses={status.HTTP_200_OK: CommonQueryClusterResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=CommonQueryClusterSerializer)
    def common_query_cluster(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        __, cluster_infos = ListRetrieveResource.common_query_cluster(**data)
        return Response(cluster_infos)

    @common_swagger_auto_schema(
        operation_summary=_("查询业务下集群的属性字段"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=QueryBizClusterAttrsSerializer(),
        responses={status.HTTP_200_OK: QueryBizClusterAttrsResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryBizClusterAttrsSerializer)
    def query_biz_cluster_attrs(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        clusters = Cluster.objects.filter(bk_biz_id=data["bk_biz_id"], cluster_type=data["cluster_type"])
        # 聚合每个属性字段
        cluster_attrs: Dict[str, Union[List, Set]] = defaultdict(list)
        existing_values: Dict[str, Set[str]] = defaultdict(set)
        if data["cluster_attrs"]:
            for attr in clusters.values(*data["cluster_attrs"]):
                for key, value in attr.items():
                    # bk_cloud_id有等于0的情况以及region字段有空字符串情况
                    if value != "" and value not in existing_values[key]:
                        existing_values[key].add(value)
                        cluster_attrs[key].append({"value": value, "text": value})

        # 如果需要查询模块信息，则需要同时提供db_module_id/db_module_name
        if "db_module_id" in cluster_attrs:
            db_modules = DBModule.objects.filter(bk_biz_id=data["bk_biz_id"], cluster_type=data["cluster_type"])
            db_module_names_map = {module.db_module_id: module.db_module_name for module in db_modules}
            cluster_attrs["db_module_id"] = [
                {"value": module, "text": db_module_names_map.get(module)}
                for module in existing_values["db_module_id"]
            ]
        # 如果需要查询管控区域信息
        if "bk_cloud_id" in cluster_attrs:
            cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
            cluster_attrs["bk_cloud_id"] = [
                {"value": bk_cloud_id, "text": cloud_info.get(str(bk_cloud_id), {}).get("bk_cloud_name", "")}
                for bk_cloud_id in existing_values["bk_cloud_id"]
            ]

        # 实例的部署角色
        if "role" in data["instances_attrs"]:
            query_filters = Q(bk_biz_id=data["bk_biz_id"], cluster_type=data["cluster_type"])
            # 获取storage实例的查询集
            storage_roles = StorageInstance.objects.filter(query_filters).values_list("instance_role", flat=True)
            # 获取proxy实例的查询集
            proxy_roles = ProxyInstance.objects.filter(query_filters).values_list("access_layer", flat=True)
            unique_roles = set(storage_roles) | (set(proxy_roles))
            roles_dicts = [{"name": role, "values": role} for role in unique_roles]
            cluster_attrs["role"] = roles_dicts

        return Response(cluster_attrs)

    @common_swagger_auto_schema(
        operation_summary=_("根据过滤条件查询集群详细信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ClusterFilterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ClusterFilterSerializer)
    def filter_clusters(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        clusters = Cluster.objects.filter(data["filters"])
        # 先按照集群类型聚合
        cluster_type__clusters: Dict[str, List[Cluster]] = defaultdict(list)
        for cluster in clusters:
            cluster_type__clusters[cluster.cluster_type].append(cluster)
        # 按照不同的集群类型，调用不同的query resource去查询集群数据
        clusters_data: List[Dict] = []
        for cluster_type, clusters in cluster_type__clusters.items():
            query_params = {"cluster_ids": [cluster.id for cluster in clusters]}
            resource_class: ListRetrieveResource = register.cluster_type__resource_class[cluster_type]
            cluster_resource_data: ResourceList = resource_class.list_clusters(
                bk_biz_id=data["bk_biz_id"], query_params=query_params, limit=-1, offset=0
            )
            clusters_data.extend(cluster_resource_data.data)

        return Response(clusters_data)

    @common_swagger_auto_schema(
        operation_summary=_("根据用户手动输入的ip[:port]查询真实的实例"),
        request_body=CheckInstancesSLZ(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: CheckInstancesResSLZ()},
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckInstancesSLZ)
    def check_instances(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        db_type = request.stream.path.split("/")[2]
        return Response(
            InstanceHandler(bk_biz_id=bk_biz_id).check_instances(
                query_instances=validated_data["instance_addresses"],
                cluster_ids=validated_data["cluster_ids"],
                db_type=db_type,
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询集群的库是否存在"),
        request_body=CheckClusterDbsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: CheckClusterDbsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckClusterDbsSerializer)
    def check_cluster_databases(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data.pop("bk_biz_id")
        return Response(ClusterServiceHandler(bk_biz_id).check_cluster_databases(**validated_data))
