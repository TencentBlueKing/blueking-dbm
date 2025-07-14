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
from backend.db_services.mongodb.toolbox.handlers import ToolboxHandler
from backend.db_services.mongodb.toolbox.serializers import (
    ExecuteClusterTcpCmdSerializer,
    GetClusterTcpResultSerializer,
)
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterActionPermission

SWAGGER_TAG = "db_services/mongodb/toolbox"


class ToolboxViewSet(BaseClusterViewSet):
    action_permission_map = {
        ("execute_cluster_tcp_cmd",): [
            ClusterActionPermission([ActionEnum.MONGODB_SOURCE_ACCESS_VIEW], ResourceEnum.MONGODB)
        ]
    }
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("执行集群来源指令"),
        request_body=ExecuteClusterTcpCmdSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ExecuteClusterTcpCmdSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=ExecuteClusterTcpCmdSerializer)
    def execute_cluster_tcp_cmd(self, request, bk_biz_id, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).execute_cluster_net_tcp_cmd(data["cluster_ids"]))

    @common_swagger_auto_schema(
        operation_summary=_("查询集群来源结果"),
        request_body=GetClusterTcpResultSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetClusterTcpResultSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetClusterTcpResultSerializer)
    def get_cluster_net_tcp_result(self, request, bk_biz_id, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(ToolboxHandler(bk_biz_id).get_cluster_proc_net_tcp(data["job_instance_id"]))
