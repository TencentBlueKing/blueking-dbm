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

from django.db.models import Count, Q
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import ResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, DBModule, ProxyInstance, StorageInstance
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.dbbase.cluster.serializers import CheckClusterDbsResponseSerializer, CheckClusterDbsSerializer
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.dbbase.instances.yasg_slz import CheckInstancesResSLZ, CheckInstancesSLZ
from backend.db_services.dbbase.resources import register
from backend.db_services.dbbase.resources.query import ListRetrieveResource, ResourceList
from backend.db_services.dbbase.resources.serializers import ClusterSLZ
from backend.db_services.dbbase.serializers import (
    ClusterDbTypeSerializer,
    ClusterEntryFilterSerializer,
    ClusterFilterSerializer,
    CommonQueryClusterResponseSerializer,
    CommonQueryClusterSerializer,
    IsClusterDuplicatedResponseSerializer,
    IsClusterDuplicatedSerializer,
    QueryAllTypeClusterResponseSerializer,
    QueryAllTypeClusterSerializer,
    QueryBizClusterAttrsResponseSerializer,
    QueryBizClusterAttrsSerializer,
    QueryClusterCapResponseSerializer,
    QueryClusterCapSerializer,
    QueryClusterInstanceCountSerializer,
    ResourceAdministrationSerializer,
    UpdateClusterAliasSerializer,
    WebConsoleResponseSerializer,
    WebConsoleSerializer,
)
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterWebconsolePermission

SWAGGER_TAG = _("集群通用接口")


class DBBaseViewSet(viewsets.SystemViewSet):
    """
    集群通用接口，用于查询/操作集群公共的属性
    """

    pagination_class = AuditedLimitOffsetPagination

    action_permission_map = {
        ("verify_duplicated_cluster_name",): [],
        (
            "simple_query_cluster",
            "common_query_cluster",
        ): [DBManagePermission()],
        ("webconsole",): [ClusterWebconsolePermission()],
    }
    default_permission_class = [DBManagePermission()]

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
        operation_summary=_("查询业务集群简略信息"),
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
        operation_summary=_("查询业务下集群通用信息"),
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
        operation_summary=_("根据过滤条件查询业务下集群详细信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ClusterFilterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ClusterFilterSerializer)
    def filter_clusters(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        # 先按照集群类型聚合
        resource_cls__cluster_ids_map = defaultdict(list)
        for cluster in Cluster.objects.filter(data["filters"]).values("id", "cluster_type"):
            resource_class = register.cluster_type__resource_class[cluster["cluster_type"]]
            resource_cls__cluster_ids_map[resource_class].append(cluster["id"])
        # 按照不同的集群类型，调用不同的query resource去查询集群数据
        clusters_data: List[Dict] = []
        for resource_class, cluster_ids in resource_cls__cluster_ids_map.items():
            if not list(cluster_ids):
                continue
            query_params = {**data["query_params"], "cluster_ids": list(cluster_ids)}
            cluster_resource_data: ResourceList = resource_class.list_clusters(
                bk_biz_id=data["bk_biz_id"], query_params=query_params, limit=-1, offset=0
            )
            clusters_data.extend(cluster_resource_data.data)

        return Response(clusters_data)

    @common_swagger_auto_schema(
        operation_summary=_("根据过滤条件查询业务下域名信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ClusterEntryFilterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ClusterEntryFilterSerializer, pagination_class=None)
    def filter_cluster_entries(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        limit, offset = data.pop("limit"), data.pop("offset")
        resource_class = register.cluster_type__resource_class[data.pop("cluster_type")]
        entry_resource_data: ResourceList = resource_class.list_cluster_entries(
            bk_biz_id=data.pop("bk_biz_id"), query_params=data, limit=limit, offset=offset
        )
        return Response({"results": entry_resource_data.data, "count": entry_resource_data.count})

    @common_swagger_auto_schema(
        operation_summary=_("根据用户手动输入的ip[:port]查询真实的实例"),
        request_body=CheckInstancesSLZ(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: CheckInstancesResSLZ()},
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckInstancesSLZ)
    def check_instances(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(
            InstanceHandler(bk_biz_id=data["bk_biz_id"]).check_instances(
                query_instances=data["instance_addresses"],
                cluster_ids=data.get("cluster_ids"),
                db_type=data.get("db_type"),
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
        clusters = Cluster.objects.filter(bk_biz_id=data["bk_biz_id"], cluster_type__in=data["cluster_type"])
        # 聚合每个属性字段
        cluster_attrs: Dict[str, Union[List, Set]] = defaultdict(list)
        existing_values: Dict[str, Set[str]] = defaultdict(set)
        # 过滤一些不合格的数据
        if data["cluster_attrs"]:
            # 获取choice map
            field__choice_map = {
                attr: {value: label for value, label in getattr(Cluster, attr).field.choices or []}
                for attr in data["cluster_attrs"]
            }
            for attr in clusters.values(*data["cluster_attrs"]):
                for key, value in attr.items():
                    # 保留bk_cloud_id有等于0的情况
                    if value is not None and value not in existing_values[key]:
                        existing_values[key].add(value)
                        cluster_attrs[key].append({"value": value, "text": field__choice_map[key].get(value, value)})

        # 如果需要查询模块信息，则需要同时提供db_module_id/db_module_name
        if "db_module_id" in cluster_attrs:
            db_modules = DBModule.objects.filter(bk_biz_id=data["bk_biz_id"], cluster_type__in=data["cluster_type"])
            if db_modules:
                db_module_names_map = {module.db_module_id: module.alias_name for module in db_modules}
                cluster_attrs["db_module_id"] = [
                    {"value": module, "text": db_module_names_map.get(module, "--")}
                    for module in existing_values["db_module_id"]
                ]
            else:
                cluster_attrs["db_module_id"] = []

        # 如果需要查询管控区域信息
        if "bk_cloud_id" in cluster_attrs:
            cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
            cluster_attrs["bk_cloud_id"] = [
                {"value": bk_cloud_id, "text": cloud_info.get(str(bk_cloud_id), {}).get("bk_cloud_name", "")}
                for bk_cloud_id in existing_values["bk_cloud_id"]
            ]

        # 实例的部署角色
        if "role" in data["instances_attrs"]:
            query_filters = Q(bk_biz_id=data["bk_biz_id"], cluster_type__in=data["cluster_type"])
            # 获取proxy实例的查询集
            proxy_roles = ProxyInstance.objects.filter(query_filters).values_list("access_layer", flat=True)
            # 获取storage实例的查询集
            storage_queryset = StorageInstance.objects.filter(query_filters)
            # mysql的实例角色返回的是InstanceInnerRole 其他集群实例InstanceRole
            if data["cluster_type"] in [ClusterType.TenDBSingle.value, ClusterType.TenDBHA.value]:
                storage_roles = storage_queryset.values_list("instance_inner_role", flat=True)
            else:
                storage_roles = storage_queryset.values_list("instance_role", flat=True)

            unique_roles = set(storage_roles) | (set(proxy_roles))
            roles_dicts = [{"value": role, "text": role} for role in unique_roles]
            cluster_attrs["role"] = roles_dicts

        return Response(cluster_attrs)

    @common_swagger_auto_schema(
        operation_summary=_("查询资源池,污点主机管理表头筛选数据"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ResourceAdministrationSerializer(),
        responses={status.HTTP_200_OK: QueryBizClusterAttrsResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ResourceAdministrationSerializer)
    def query_resource_administration_attrs(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @common_swagger_auto_schema(
        operation_summary=_("webconsole查询"),
        request_body=WebConsoleSerializer(),
        responses={status.HTTP_200_OK: WebConsoleResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=WebConsoleSerializer)
    def webconsole(self, request):
        data = self.params_validate(self.get_serializer_class())
        cluster = Cluster.objects.get(id=data["cluster_id"])
        db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        # mysql / tendbcluster
        if db_type in [DBType.MySQL, DBType.TenDBCluster]:
            from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler

            return Response(RemoteServiceHandler(bk_biz_id=cluster.bk_biz_id).webconsole_rpc(**data))
        elif db_type in ClusterType.redis_cluster_types():
            from backend.db_services.redis.toolbox.handlers import ToolboxHandler

            return Response(ToolboxHandler.webconsole_rpc(**data))

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询ip列表"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ClusterDbTypeSerializer(),
        responses={status.HTTP_200_OK: ClusterDbTypeSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=ClusterDbTypeSerializer,
    )
    def get_ips_list(self, request, *args, **kwargs):
        # 接收参数
        db_type = self.validated_data["db_type"]
        bk_biz_id = self.validated_data["bk_biz_id"]

        # db类型为InfluxDB, 则直接返回
        if db_type == DBType.InfluxDB:
            return Response(
                StorageInstance.objects.filter(instance_role=InstanceRole.INFLUXDB).values_list(
                    "machine__ip", flat=True
                )
            )

        # 获取所有符合条件的集群对象
        clusters = Cluster.objects.prefetch_related(
            "storageinstance_set", "proxyinstance_set", "storageinstance_set__machine", "proxyinstance_set__machine"
        ).filter(bk_biz_id=bk_biz_id, cluster_type__in=ClusterType.db_type_to_cluster_types(db_type))

        ips = []
        # 遍历集群对象，获取符合条件的ip
        for cluster in clusters:
            ips.extend(cluster.proxyinstance_set.all().values_list("machine__ip", flat=True))
            ips.extend(cluster.storageinstance_set.all().values_list("machine__ip", flat=True))
        return Response(ips)

    @common_swagger_auto_schema(
        operation_summary=_("根据业务id查询业务下所有集群集群数量与实例数量"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=QueryClusterInstanceCountSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryClusterInstanceCountSerializer)
    def query_cluster_instance_count(self, request, *args, **kwargs):
        validate_data = self.params_validate(self.get_serializer_class())
        cluster_queryset = Cluster.objects.filter(**validate_data)
        storage_instance_queryset = StorageInstance.objects.filter(**validate_data)
        proxy_instance_queryset = ProxyInstance.objects.filter(**validate_data)
        # 统计每种 cluster_type 的数量
        cluster_type_counts = list(cluster_queryset.values("cluster_type").annotate(count=Count("cluster_type")))
        storage_type_counts = list(
            storage_instance_queryset.values("cluster_type").annotate(count=Count("cluster_type"))
        )
        proxy_type_counts = list(proxy_instance_queryset.values("cluster_type").annotate(count=Count("cluster_type")))

        # 将列表转化为字典以便处理
        def list_to_dict(type_counts):
            return {entry["cluster_type"]: entry["count"] for entry in type_counts}

        # 转换为字典
        cluster_type_dict = list_to_dict(cluster_type_counts)
        storage_type_dict = list_to_dict(storage_type_counts)
        proxy_type_dict = list_to_dict(proxy_type_counts)

        # 合并 storage 和 proxy 的类型计数
        instance_count_dict = defaultdict(int)
        for cluster_type, count in storage_type_dict.items():
            instance_count_dict[cluster_type] += count
        for cluster_type, count in proxy_type_dict.items():
            instance_count_dict[cluster_type] += count

        # 计算 Redis 相关类型的总计数
        redis_cluster_count = 0
        redis_instance_count = 0

        redis_cluster_types = ClusterType.redis_cluster_types()
        redis_cluster_types.remove(ClusterType.TendisRedisInstance)

        for cluster_type in redis_cluster_types:
            redis_cluster_count += cluster_type_dict.get(cluster_type, 0)
            redis_instance_count += instance_count_dict.get(cluster_type, 0)

        # 构建最终输出格式，包含所有 ClusterType 成员
        cluster_type_count_map = {}
        for cluster_type in ClusterType.get_values():
            if cluster_type not in redis_cluster_types:
                cluster_count = cluster_type_dict.get(cluster_type, 0)
                instance_count = instance_count_dict.get(cluster_type, 0)
                cluster_type_count_map[cluster_type] = {
                    "cluster_count": cluster_count,
                    "instance_count": instance_count,
                }
        cluster_type_count_map["redis_cluster"] = {
            "cluster_count": redis_cluster_count,
            "instance_count": redis_instance_count,
        }

        return Response(cluster_type_count_map)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群容量"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=QueryClusterCapSerializer(),
        responses={status.HTTP_200_OK: QueryClusterCapResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryClusterCapSerializer, pagination_class=None)
    def query_cluster_stat(self, request, *args, **kwargs):
        from backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat import sync_cluster_stat_by_cluster_type

        data = self.params_validate(self.get_serializer_class())
        cluster_stat_map = {}
        for cluster_type in data["cluster_type"].split(","):
            cluster_stat_map.update(sync_cluster_stat_by_cluster_type(data["bk_biz_id"], cluster_type))

        cluster_domain_qs = Cluster.objects.filter(bk_biz_id=3).values("immute_domain", "id")
        cluster_domain_map = {cluster["immute_domain"]: cluster["id"] for cluster in cluster_domain_qs}
        cluster_stat_map = {
            cluster_domain_map[domain]: cap for domain, cap in cluster_stat_map.items() if domain in cluster_domain_map
        }

        return Response(cluster_stat_map)

    @common_swagger_auto_schema(
        operation_summary=_("更新集群别名"),
        request_body=UpdateClusterAliasSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateClusterAliasSerializer)
    def update_cluster_alias(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        """更新集群别名"""
        cluster = Cluster.objects.get(bk_biz_id=validated_data["bk_biz_id"], id=validated_data["cluster_id"])
        cluster.alias = validated_data["new_alias"]
        cluster.save(update_fields=["alias"])
        serializer = ClusterSLZ(cluster)
        return Response(serializer.data)
