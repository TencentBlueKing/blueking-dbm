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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs, auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl import mip_action as mip_action_impl
from backend.dbm_aiagent.mcp_tools.redis.serializers.mip_action import (
    AnalyzeMipCapacityInputSerializer,
    AnalyzeMipCapacityOutputSerializer,
    EvaluateMipActionInputSerializer,
    EvaluateMipActionOutputSerializer,
    GetClusterSpecInputSerializer,
    GetClusterSpecOutputSerializer,
    GetSupportedQpsInputSerializer,
    GetSupportedQpsOutputSerializer,
    ListLastFailedClustersInputSerializer,
    ListLastFailedClustersOutputSerializer,
    ListMipActionsInputSerializer,
    ListMipActionsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import (
    McpBizManageOrDbaPermission,
    McpClusterDetailPermission,
    McpDBManagePermission,
)

logger = logging.getLogger("root")


class MipActionMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询已提交的 MIP Action 容量评估请求记录（来自 tb_capacity_evaluate_request）")),
        request_slz=ListMipActionsInputSerializer,
        response_slz=ListMipActionsOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def list_mip_actions(self, request, *args, **kwargs):
        return Response(
            mip_action_impl.list_mip_actions(
                bk_biz_id=self.get_param("bk_biz_id"),
                action_id=self.get_param("action_id") or None,
                cluster_domain=self.get_param("cluster_domain") or None,
                limit=self.get_param("limit") or 50,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("仅对已提交的 MIP Action 发起容量重评；不新建 action")),
        request_slz=EvaluateMipActionInputSerializer,
        response_slz=EvaluateMipActionOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def evaluate_mip_action(self, request, *args, **kwargs):
        return Response(
            mip_action_impl.evaluate_mip_action(
                bk_biz_id=self.get_param("bk_biz_id"),
                action_id=self.get_param("action_id"),
                cluster_domain=self.get_param("cluster_domain") or None,
                is_force=self.get_param("is_force"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("按当前容量评估模型，返回 Redis 集群可支持的 QPS（单位 K，含 proxy/backend 分项）")),
        request_slz=GetSupportedQpsInputSerializer,
        response_slz=GetSupportedQpsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def get_supported_qps(self, request, *args, **kwargs):
        return Response(mip_action_impl.get_supported_qps(cluster_domain=self.get_param("cluster_domain")))

    @mcp_tools_api_decorator(
        description=str(_("分析集群 MIP 容量：时间窗内未结束 Action、重叠峰值 QPS/容量、" "最近评估历史与扩容建议（只读，不新建/不重评 Action）")),
        request_slz=AnalyzeMipCapacityInputSerializer,
        response_slz=AnalyzeMipCapacityOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def analyze_mip_capacity(self, request, *args, **kwargs):
        return Response(
            mip_action_impl.analyze_mip_capacity(
                cluster_domain=self.get_param("cluster_domain"),
                current_time=self.get_param("current_time") or None,
                stop_time=self.get_param("stop_time") or None,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("按域名返回 Redis 集群精简拓扑规格（proxy/分片数与规格串，不含主机明细）")),
        request_slz=GetClusterSpecInputSerializer,
        response_slz=GetClusterSpecOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def get_cluster_spec(self, request, *args, **kwargs):
        return Response(mip_action_impl.get_cluster_spec(cluster_domain=self.get_param("cluster_domain")))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出最近一次容量评估失败（approved_status 为 failed/error）的集群域名；"
                "传 bk_biz_id 按业务过滤并校验业务管理权限；"
                "不传 bk_biz_id 时仅 DBA 可查全业务。按各集群最新一条 history 判定"
            )
        ),
        request_slz=ListLastFailedClustersInputSerializer,
        response_slz=ListLastFailedClustersOutputSerializer,
        permission_classes=[McpBizManageOrDbaPermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_CAPACITY],
        name_prefix="redis_capacity",
    )
    def list_last_failed_clusters(self, request, *args, **kwargs):
        return Response(
            mip_action_impl.list_last_failed_clusters(
                bk_biz_id=self.get_param("bk_biz_id"),
                limit=self.get_param("limit") or 100,
            )
        )
