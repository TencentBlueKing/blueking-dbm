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
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta import api
from backend.db_meta.api import dbha as DBHA
from backend.db_meta.api.cluster import nosqlcomm as NOSQLMETA
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import BKCity
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.db_meta.serializers import (
    BizClusterSerializer,
    BKCityNameSerializer,
    ClusterDetailSerializer,
    EntryDetailSerializer,
    FakeResetTendbHACluster,
    FakeTendbHACreateCluster,
    FakeTendbSingleCreateCluster,
    InstancesResponseSerializer,
    InstancesSerializer,
    MachinesClusterSerializer,
    SwapRoleSerializer,
    TendbInstancesSerializer,
    TendisClusterSwapSerializer,
    UpdateStatusSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet


class DBMetaApiProxyPassViewSet(BaseProxyPassViewSet):
    """
    DBMeta接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]过滤实例列表"),
        request_body=InstancesSerializer(),
        responses={status.HTTP_200_OK: InstancesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=InstancesSerializer, url_path="dbmeta/dbha/instances")
    def instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.instances(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]实例角色交换"),
        request_body=SwapRoleSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SwapRoleSerializer, url_path="dbmeta/dbha/swap_role")
    def swap_role(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.swap_role(validated_data["payloads"], validated_data["bk_cloud_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]sqlserver实例角色交换"),
        request_body=SwapRoleSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=SwapRoleSerializer,
        url_path="dbmeta/dbha/sqlserver_cluster_swap",
    )
    def sqlserver_swap_role(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.sqlserver_cluster_swap(validated_data["payloads"], validated_data["bk_cloud_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]tendis集群交换"),
        request_body=TendisClusterSwapSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendisClusterSwapSerializer,
        url_path="dbmeta/dbha/tendis_cluster_swap",
    )
    def tendis_cluster_swap(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.tendis_cluster_swap(validated_data["payload"], validated_data["bk_cloud_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]状态更新"),
        request_body=UpdateStatusSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=UpdateStatusSerializer, url_path="dbmeta/dbha/update_status"
    )
    def update_status(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.update_status(validated_data["payloads"], validated_data["bk_cloud_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]查询entry信息"),
        request_body=EntryDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=EntryDetailSerializer, url_path="dbmeta/dbha/entry_detail"
    )
    def entry_detail(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.entry_detail(validated_data["domains"]))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]根据逻辑城市查询具体城市名称"),
        request_body=BKCityNameSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BKCityNameSerializer, url_path="dbmeta/bk_city_name")
    def bk_city_name(self, request):
        logic_city_name = self.params_validate(self.get_serializer_class())["logic_city_name"]
        bk_city_name = BKCity.objects.filter(logical_city__name=logic_city_name).values_list(
            "bk_idc_city_name", flat=True
        )
        return Response(list(set(bk_city_name)))

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]构建测试单节点集群数据"),
        request_body=FakeTendbSingleCreateCluster(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=FakeTendbSingleCreateCluster,
        url_path="dbmeta/fake/tendbsingle/create_cluster",
    )
    def fake_tendbsingle_create_cluster(self, request):
        try:
            return Response({"msg": "", "code": 0, "data": api.fake.fake_create_tendbsingle(**request.data)})
        except Exception as e:  # pylint: disable=broad-except
            return Response({"msg": "{}".format(e), "code": 1, "data": ""})

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]构建测试高可用集群数据"),
        request_body=FakeTendbHACreateCluster(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=FakeTendbHACreateCluster,
        url_path="dbmeta/fake/tendbha/create_cluster",
    )
    def fake_tendbha_create_cluster(self, request):
        try:
            return Response({"msg": "", "code": 0, "data": api.fake.fake_create_tendbha_cluster(**request.data)})
        except Exception as e:  # pylint: disable=broad-except
            return Response({"msg": "{}".format(e), "code": 1, "data": ""})

    # 批量查询主机信息
    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]查询主机信息"),
        request_body=MachinesClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=MachinesClusterSerializer,
        url_path="dbmeta/meta/machines_detail",
    )
    def machines_detail(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBHA.query_cluster_by_hosts(validated_data["hosts"]))

    # 批量查询redis集群信息
    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]查询redis集群信息"),
        request_body=ClusterDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=ClusterDetailSerializer,
        url_path="dbmeta/meta/clusters_detail",
    )
    def clusters_detail(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(NOSQLMETA.get_clusters_details(validated_data["cluster_ids"]))

    # fake重置dbha集群
    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]fake重置dbha集群"),
        request_body=FakeResetTendbHACluster(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=FakeResetTendbHACluster,
        url_path="dbmeta/meta/fake_reset_tendbha_cluster",
    )
    def fake_reset_tendbha_cluster(self, request):
        try:
            return Response({"msg": "", "code": 0, "data": api.fake.fake_reset_tendbha_cluster(**request.data)})
        except Exception as e:  # pylint: disable=broad-except
            return Response({"msg": "{}".format(e), "code": 1, "data": ""})

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager根据域名查询集群信息"),
        query_serializer=BizClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=BizClusterSerializer,
        url_path="dbmeta/priv_manager/biz_clusters",
    )
    def biz_clusters(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.biz_clusters(
            bk_biz_id=validated_data["bk_biz_id"],
            immute_domains=validated_data["immute_domains"],
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询tendbsingle集群实例信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/mysql/tendbsingle/cluster_instances",
    )
    def tendbsingle_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.mysql.cluster_instances.tendbsingle(entry_name=validated_data.get("entry_name"))
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询tendbha集群实例信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/mysql/tendbha/cluster_instances",
    )
    def tendbha_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.mysql.cluster_instances.tendbha(entry_name=validated_data.get("entry_name"))
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询tendbcluster集群实例信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/mysql/tendbcluster/cluster_instances",
    )
    def tendbcluster_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.mysql.cluster_instances.tendbcluster(entry_name=validated_data.get("entry_name"))
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询delegated_mysql集群信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/delegated_mysql/cluster_instances",
    )
    def delegated_mysql_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.mysql.cluster_instances.delegated_mysql(validated_data.get("entry_name"))
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询SqlserverHA集群信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/sqlserver/sqlserver_ha/cluster_instances",
    )
    def sqlserver_ha_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.sqlserver.cluster_instances(
            immute_domain=validated_data.get("entry_name"),
            cluster_type=ClusterType.SqlserverHA.value,
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("[dbmeta]priv_manager查询SqlserverSingle集群信息"),
        request_body=TendbInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TendbInstancesSerializer,
        url_path="dbmeta/priv_manager/sqlserver/sqlserver_single/cluster_instances",
    )
    def sqlserver_single_cluster_instances(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = api.priv_manager.sqlserver.cluster_instances(
            immute_domain=validated_data.get("entry_name"),
            cluster_type=ClusterType.SqlserverSingle.value,
        )
        return Response(data)
