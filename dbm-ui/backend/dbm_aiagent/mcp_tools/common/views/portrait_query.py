# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 MCP - 视图层。

模块职责：
    - 挂载 2 个 MCP 工具：
        * ``portrait_discover_dimensions``：查询可用维度清单（无 cluster/biz 上下文，不做资源鉴权）
        * ``portrait_fetch_summaries``    ：按集群 + 维度批量拉取"时间窗内全部匹配"摘要
          （**不做「每 code 取最新」聚合**，走集群资源鉴权）
    - 视图只做"参数取值 + 转发 impl 层"，不承载业务逻辑
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.portrait_query import PortraitQueryService
from backend.dbm_aiagent.mcp_tools.common.serializers.portrait_query import (
    PortraitDiscoverDimensionsInputSerializer,
    PortraitDiscoverDimensionsOutputSerializer,
    PortraitFetchSummariesInputSerializer,
    PortraitFetchSummariesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission


class PortraitQueryMcpToolsViewSet(McpToolsViewSet):
    """集群画像 MCP 工具视图集。

    职责：
        - 提供 discover / fetch_summaries 两个只读 MCP 工具，供 Agent 生成集群画像报告时调用
        - 未挂装饰器的默认路径由 ``default_permission_class`` 兜底拒绝，防止误暴露

    边界：
        - 本视图**只读**；写侧走 SDK 的 ``ingest_summary`` 由各巡检维度自行完成，不在 MCP 通道
    """

    #: 类级默认权限：非 MCP 装饰器方法一律拒绝，防止未装饰路径被误暴露
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _("集群画像 - 发现可用维度：返回当前所有启用中的巡检维度（含 code / name / description），" "供 Agent 决定本轮画像分析要采集哪些维度。可选按 db_type 过滤。")
        ),
        request_slz=PortraitDiscoverDimensionsInputSerializer,
        response_slz=PortraitDiscoverDimensionsOutputSerializer,
        tags=[DBMMCPTags.READ],
        # discover 无 cluster/biz 入参，走"空权限"分支（等价于装饰器侧不做资源鉴权）
        permission_classes=[],
        mcp=[DBMMcpTools.PORTRAIT_QUERY],
        name_prefix="portrait_query",
    )
    def portrait_discover_dimensions(self, request, *args, **kwargs):
        """MCP 工具：portrait_discover_dimensions。

        参见类 docstring；实际业务实现在 ``PortraitQueryService.discover_dimensions``。
        """
        db_type: str = self.get_param("db_type", "")
        return Response(PortraitQueryService.discover_dimensions(db_type=db_type or None))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "集群画像 - 拉取维度摘要（时间范围内全部匹配）：按 (bk_biz_id, cluster_domain) 批量取"
                "指定维度 codes 在时间窗内的**全部**巡检摘要记录；同一 code 在时间窗内多次上报会返回多条，"
                "不做「每 code 取最新」的聚合。codes 不传时默认取该集群 db_type 下所有启用维度。"
            )
        ),
        request_slz=PortraitFetchSummariesInputSerializer,
        response_slz=PortraitFetchSummariesOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.PORTRAIT_QUERY],
        name_prefix="portrait_query",
    )
    def portrait_fetch_summaries(self, request, *args, **kwargs):
        """MCP 工具：portrait_fetch_summaries。

        参见类 docstring；实际业务实现在 ``PortraitQueryService.fetch_summaries``。
        """
        bk_biz_id: int = int(self.get_param("bk_biz_id"))
        cluster_domain: str = self.get_param("cluster_domain")
        codes = self.get_param("codes", None)
        since = self.get_param("since", None)
        until = self.get_param("until", None)
        return Response(
            PortraitQueryService.fetch_summaries(
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
                codes=codes,
                since=since,
                until=until,
            )
        )
