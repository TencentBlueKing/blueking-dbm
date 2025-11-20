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

from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.db_meta.models import Cluster
from backend.db_services.dbbase.views import DBBaseViewSet
from backend.dbm_aiagent.mcp_tools.common.serializers import (
    FilterClusterInputSerializer,
    FilterClusterOutputSerializer,
    GetClusterBaseInfoInputSerializer,
    GetClusterBaseInfoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet


class ClusterMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = []

    @mcp_tools_api_decorator(
        description=_("获取集群的业务和类型基础信息(无鉴权)"),
        request_slz=GetClusterBaseInfoInputSerializer,
        response_slz=GetClusterBaseInfoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.DBM],
    )
    def get_cluster_base_info(self, request, *args, **kwargs):
        domain = self.params_validate(self.get_serializer_class())["cluster_domain"]
        cluster = Cluster.objects.filter(immute_domain__in=domain).values(
            "bk_biz_id", "cluster_type", "immute_domain", "id"
        )
        return Response(list(cluster))

    @mcp_tools_api_decorator(
        description=_("获取集群详细信息"),
        request_slz=FilterClusterInputSerializer,
        response_slz=FilterClusterOutputSerializer,
        reference_view=DBBaseViewSet.filter_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.DBM],
    )
    def filter_clusters(self, request, *args, **kwargs):
        return Response()
