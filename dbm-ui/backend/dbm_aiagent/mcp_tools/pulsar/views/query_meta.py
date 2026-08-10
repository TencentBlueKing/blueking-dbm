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
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.pulsar.impl.cluster_meta import (
    cluster_overview,
    list_biz_by_name,
    list_my_pulsar_bizs,
    pulsar_list_clusters,
    search_specs_by_name,
)
from backend.dbm_aiagent.mcp_tools.pulsar.serializers.cluster_meta import (
    PulsarBizDetailSerializer,
    PulsarBizInputSerializer,
    PulsarBizNameInputSerializer,
    PulsarClusterInputSerializer,
    PulsarClusterOutputSerializer,
    PulsarNoArgsInputSerializer,
    PulsarTopoOutputSerializer,
    SpecOutputSerializer,
    SpecSearchInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Pulsar meta 相关的 query
"""


class PulsarQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询我负责的Pulsar业务列表，无需入参，按当前调用用户返回其负责的业务")),
        request_slz=PulsarNoArgsInputSerializer,
        response_slz=PulsarBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_QUERY_META],
        name_prefix="pulsar_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_pulsar_bizs(userID=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("根据业务英文名查询业务详情")),
        request_slz=PulsarBizNameInputSerializer,
        response_slz=PulsarBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_QUERY_META],
        name_prefix="pulsar_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        biz_name = self.get_param("biz_name")
        return Response(list_biz_by_name(biz_name=biz_name))

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的Pulsar集群列表，返回每个集群的broker/bookkeeper/zookeeper节点数量和版本信息")),
        request_slz=PulsarBizInputSerializer,
        response_slz=PulsarClusterOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_QUERY_META],
        name_prefix="pulsar_query_meta",
    )
    def list_pulsar_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        return Response(pulsar_list_clusters(bk_biz_id=bk_biz_id))

    @mcp_tools_api_decorator(
        description=str(_("查询 Pulsar 集群信息，按 broker/bookkeeper/zookeeper 三个角色分别返回节点明细、状态分布和规格信息")),
        request_slz=PulsarClusterInputSerializer,
        response_slz=PulsarTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_QUERY_META],
        name_prefix="pulsar_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        return Response(cluster_overview(immute_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("根据规格名称模糊查询规格信息，支持如 '16核32G' 等规格名称搜索")),
        request_slz=SpecSearchInputSerializer,
        response_slz=SpecOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_QUERY_META],
        name_prefix="pulsar_query_meta",
    )
    def search_specs_by_name(self, request, *args, **kwargs):
        spec_name = self.get_param("spec_name")
        spec_cluster_type = self.get_param("spec_cluster_type", ClusterType.Pulsar.value)
        return Response(search_specs_by_name(spec_name=spec_name, spec_cluster_type=spec_cluster_type))
