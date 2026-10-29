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

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.doris.impl.cluster_meta import (
    cluster_overview,
    doris_list_clusters,
    list_biz_by_name,
    list_my_doris_bizs,
    search_doris_specs_by_name,
)
from backend.dbm_aiagent.mcp_tools.doris.serializers.cluster_meta import (
    DorisBizDetailSerializer,
    DorisBizInputSerializer,
    DorisBizNameInputSerializer,
    DorisClusterInputSerializer,
    DorisClusterListOutputSerializer,
    DorisClusterOverviewOutputSerializer,
    DorisNoArgsInputSerializer,
    DorisSpecOutputSerializer,
    DorisSpecSearchInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")

"""
Doris meta 相关的 query
- 业务与集群发现
- 集群概览（节点数量与规格，不含监控指标）
- 规格模糊搜索
"""


class DorisQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询当前用户作为主负责人管理的所有 Doris 业务列表。" "当用户未提供 bk_biz_id 时，应先调用此接口获取可用业务列表。")),
        request_slz=DorisNoArgsInputSerializer,
        response_slz=DorisBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_QUERY_META],
        name_prefix="doris_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_doris_bizs(username=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("通过业务英文名（模糊匹配）查询业务信息。" "当用户提供了业务名称但未提供 bk_biz_id 时，应先调用此接口将名称转换为 bk_biz_id。")),
        request_slz=DorisBizNameInputSerializer,
        response_slz=DorisBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_QUERY_META],
        name_prefix="doris_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(list_biz_by_name(biz_name=validated_params["biz_name"]))

    @mcp_tools_api_decorator(
        description=str(
            _("查询指定业务（bk_biz_id）下的所有 Doris 集群列表，" "每个集群附带域名、别名、版本、地域，以及按节点角色的节点数量。" "未部署的角色不会出现在 role_node_counts 中。")
        ),
        request_slz=DorisBizInputSerializer,
        response_slz=DorisClusterListOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_QUERY_META],
        name_prefix="doris_query_meta",
    )
    def list_doris_clusters(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(doris_list_clusters(bk_biz_id=validated_params["bk_biz_id"]))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 Doris 集群概览：集群基本属性，以及按节点角色的节点数量与规格统计。"
                "角色分为 FE 层(doris_follower / doris_observer)与 "
                "BE 层(doris_backend_hot / doris_backend_warm / doris_backend_cold)，"
                "每个角色给出节点数、机器数、实例状态分布、版本清单、规格分布与规格详情，"
                "并附 FE / BE 两层的节点数与机器数汇总。"
                "注意三点: "
                "(1) 只返回统计信息，不返回逐节点的 IP 与端口清单; "
                "(2) 集群中未部署的角色不会出现在结果里，例如多数集群没有 Observer 节点; "
                "(3) 本工具只返回平台元数据，不含 CPU / 磁盘 / 容量等使用量信息，"
                "需要使用量与水位请调用 doris-metrics 的指标查询工具。"
            )
        ),
        request_slz=DorisClusterInputSerializer,
        response_slz=DorisClusterOverviewOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_QUERY_META],
        name_prefix="doris_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(cluster_overview(cluster_domain=validated_params["cluster_domain"]))

    @mcp_tools_api_decorator(
        description=str(_("根据规格名称模糊查询 Doris 规格信息，支持如 '16核32G' 等规格名称搜索，" "返回规格 ID、名称、机器类型、CPU、内存、磁盘与描述。无匹配时返回空列表。")),
        request_slz=DorisSpecSearchInputSerializer,
        response_slz=DorisSpecOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_QUERY_META],
        name_prefix="doris_query_meta",
    )
    def search_specs_by_name(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(search_doris_specs_by_name(spec_name=validated_params["spec_name"]))
