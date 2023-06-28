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
from backend.db_services.redis.toolbox.handlers import ToolboxHandler
from backend.db_services.redis.toolbox.serializers import (
    QueryByClusterResultSerializer,
    QueryByClusterSerializer,
    QueryByIpResultSerializer,
    QueryByIpSerializer,
    QueryByOneClusterSerializer,
    QueryClusterIpsSerializer,
    QueryMasterSlaveByIpResultSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/redis/toolbox"


class ToolboxViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("根据IP查询集群、角色和规格"),
        request_body=QueryByIpSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryByIpResultSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryByIpSerializer)
    def query_by_ip(self, request, bk_biz_id, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).query_by_ip(validated_data["ips"]))

    @common_swagger_auto_schema(
        operation_summary=_("根据masterIP查询集群、实例和slave"),
        request_body=QueryByIpSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryMasterSlaveByIpResultSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryByIpSerializer)
    def query_master_slave_by_ip(self, request, bk_biz_id, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).query_master_slave_by_ip(validated_data["ips"]))

    @common_swagger_auto_schema(
        operation_summary=_("批量过滤获取集群相关信息"),
        request_body=QueryByClusterSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryByClusterResultSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryByClusterSerializer)
    def query_by_cluster(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            ToolboxHandler(bk_biz_id).query_by_cluster(
                validated_data["keywords"],
                validated_data.get("role", "all"),
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询集群下的主机列表"),
        request_body=QueryClusterIpsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryClusterIpsSerializer, pagination_class=None)
    def query_cluster_ips(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
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
        operation_summary=_("根据业务ID查询集群列表"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=None, pagination_class=None)
    def query_cluster_list(self, request, bk_biz_id, **kwargs):
        return Response(ToolboxHandler(bk_biz_id).query_cluster_list())
