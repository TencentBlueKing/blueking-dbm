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
from backend.dbm_aiagent.mcp_tools.hdfs.impl.cluster_meta import (
    cluster_overview,
    hdfs_list_clusters,
    list_biz_by_name,
    list_cluster_nodes,
    list_my_hdfs_bizs,
    search_hdfs_specs_by_name,
)
from backend.dbm_aiagent.mcp_tools.hdfs.serializers.cluster_meta import (
    HdfsBizDetailSerializer,
    HdfsBizInputSerializer,
    HdfsBizNameInputSerializer,
    HdfsClusterInputSerializer,
    HdfsClusterListOutputSerializer,
    HdfsClusterNodesInputSerializer,
    HdfsClusterNodesOutputSerializer,
    HdfsClusterOverviewOutputSerializer,
    HdfsNoArgsInputSerializer,
    HdfsSpecOutputSerializer,
    HdfsSpecSearchInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")

"""
HDFS meta 相关的 query
- 业务与集群发现
- 集群概览（节点数量与规格，不含监控指标）
- 规格模糊搜索
"""


class HdfsQueryMetaMcpToolsViewSet(McpToolsViewSet):
    # 当前 HDFS MCP 功能仅对后台 admin 身份开放。
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询当前用户作为主负责人管理的所有 HDFS 业务列表。" "当用户未提供 bk_biz_id 时，应先调用此接口获取可用业务列表。")),
        request_slz=HdfsNoArgsInputSerializer,
        response_slz=HdfsBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_hdfs_bizs(username=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("通过业务英文名（模糊匹配）查询业务信息。" "当用户提供了业务名称但未提供 bk_biz_id 时，应先调用此接口将名称转换为 bk_biz_id。")),
        request_slz=HdfsBizNameInputSerializer,
        response_slz=HdfsBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(list_biz_by_name(biz_name=validated_params["biz_name"]))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询指定业务（bk_biz_id）下的所有 HDFS 集群列表，"
                "每个集群附带域名、别名、版本、地域，以及按节点角色的节点数量。"
                "角色取值为 hdfs_namenode / hdfs_datanode / hdfs_journalnode / hdfs_zookeeper，"
                "未部署的角色不会出现在 role_node_counts 中。"
                "注意 zookeeper / journalnode / namenode 三类实例部署在同一批 master 机器上，"
                "三者节点数之和不等于机器数。"
            )
        ),
        request_slz=HdfsBizInputSerializer,
        response_slz=HdfsClusterListOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def list_hdfs_clusters(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(hdfs_list_clusters(bk_biz_id=validated_params["bk_biz_id"]))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 HDFS 集群概览：集群基本属性，以及按节点角色的节点数量与规格统计。"
                "覆盖全部四个角色 hdfs_namenode / hdfs_datanode / hdfs_journalnode / hdfs_zookeeper，"
                "每个角色给出节点数、机器数、实例状态分布、版本清单、规格分布与规格详情，"
                "并附 master 层与 datanode 层的节点数与机器数汇总。"
                "注意四点: "
                "(1) 只返回统计信息，不返回逐节点的 IP 与端口清单，需要节点明细请调用 list_cluster_nodes; "
                "(2) 集群中未部署的角色不会出现在结果里，可据此判断集群是否具备 HA 条件"
                "（HA 集群应同时有 namenode、journalnode、zookeeper 三个角色）; "
                "(3) 本工具只返回平台元数据，不含 CPU / 磁盘 / 容量等使用量信息，"
                "需要使用量与水位请调用 hdfs-metrics 的指标查询工具。"
            )
        ),
        request_slz=HdfsClusterInputSerializer,
        response_slz=HdfsClusterOverviewOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(cluster_overview(cluster_domain=validated_params["cluster_domain"]))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "按角色列出 HDFS 集群的节点明细，每个实例返回 ip、port、instance_id、instance_role、status、"
                "bk_host_id、bk_cloud_id 等字段。"
                "bk_host_id / bk_cloud_id 定位主机，ip / port 定位实例进程，instance_id 是实例在平台内的唯一 ID，"
                "任何需要引用具体节点的场景都应从本工具获取这些值，禁止自行推测或编造。"
                "注意三点: "
                "(1) 可用 instance_roles 按角色过滤，通常只需 hdfs_datanode; "
                "(2) 用户只提供了 IP 时，通过 ips 参数反查，未匹配到的 IP 会列在 unmatched_ips 中，"
                "此时应向用户确认而不是忽略; "
                "(3) 同一台 master 机器上的 zookeeper、journalnode、namenode 是三个独立实例，"
                "会以同一 IP、不同端口出现多次，按实例（ip:port）区分，不要去重。"
            )
        ),
        request_slz=HdfsClusterNodesInputSerializer,
        response_slz=HdfsClusterNodesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def list_cluster_nodes(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(
            list_cluster_nodes(
                cluster_domain=validated_params["cluster_domain"],
                instance_roles=validated_params.get("instance_roles"),
                ips=validated_params.get("ips"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "根据规格名称模糊查询 HDFS 规格信息，支持如 '16核32G' 等规格名称搜索，"
                "返回规格 ID、名称、机器类型、CPU、内存、磁盘与描述。"
                "机器类型 hdfs_master 承载 zookeeper/journalnode/namenode，hdfs_datanode 承载 datanode。"
                "无匹配时返回空列表。"
            )
        ),
        request_slz=HdfsSpecSearchInputSerializer,
        response_slz=HdfsSpecOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_QUERY_META],
        name_prefix="hdfs_query_meta",
    )
    def search_specs_by_name(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(search_hdfs_specs_by_name(spec_name=validated_params["spec_name"]))
