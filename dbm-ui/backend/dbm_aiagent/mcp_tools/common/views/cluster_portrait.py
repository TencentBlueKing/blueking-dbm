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
    - 挂载 3 个 MCP 工具：
        * ``portrait_discover_dimensions``：按 (bk_biz_id, cluster_domain) 反查集群 db_type，
          返回该集群 db_type 下所有启用中的巡检维度（走集群资源鉴权）
        * ``portrait_fetch_summaries``    ：按集群 + 维度批量拉取"时间窗内全部匹配"摘要
          （**不做「每 code 取最新」聚合**，走集群资源鉴权）
        * ``portrait_ingest_summary``     ：写入一条集群维度巡检摘要（走集群资源鉴权）
    - 视图只做"参数取值 + 转发 impl 层"，不承载业务逻辑
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.portrait_ingest import PortraitIngestService
from backend.dbm_aiagent.mcp_tools.common.impl.portrait_query import PortraitQueryService
from backend.dbm_aiagent.mcp_tools.common.serializers.portrait_query import (
    PortraitDiscoverDimensionsInputSerializer,
    PortraitDiscoverDimensionsOutputSerializer,
    PortraitFetchSummariesInputSerializer,
    PortraitFetchSummariesOutputSerializer,
    PortraitIngestSummaryInputSerializer,
    PortraitIngestSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission


class ClusterPortraitMcpToolsViewSet(McpToolsViewSet):
    """集群画像 MCP 工具视图集。

    职责：
        - 提供 discover / fetch_summaries / ingest_summary 三个 MCP 工具，
          分别用于「发现可用维度」「读取时间窗内摘要」「写入巡检摘要」
        - 未挂装饰器的默认路径由 ``default_permission_class`` 兜底拒绝，防止误暴露

    边界：
        - 读侧（discover / fetch_summaries）与写侧（ingest_summary）均对外暴露
        - 写侧原生入口仍是 SDK ``ingest_summary``（供本进程内直接调用）；
          本视图仅为跨进程 / Agent 通道下的写入适配
    """

    #: 类级默认权限：非 MCP 装饰器方法一律拒绝，防止未装饰路径被误暴露
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "集群画像 - 发现集群启用维度：按 (bk_biz_id, cluster_domain) 反查集群 db_type，"
                "返回该集群 db_type 下所有启用中的巡检维度（含 dimension_code / name / description / "
                "weight / summary_fetch_strategy），供 Agent 决定本轮画像分析要采集哪些维度。"
                "其中 summary_fetch_strategy 表示拉取该维度摘要时应采用的策略（all 返回全部 / "
                "last 返回最新一条 / first 返回最老一条），weight 为该维度综合评分权重（未配置为 null）。"
                "集群不存在时通过 status=cluster_not_found 返回。"
            )
        ),
        request_slz=PortraitDiscoverDimensionsInputSerializer,
        response_slz=PortraitDiscoverDimensionsOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.CLUSTER_PORTRAIT],
        name_prefix="cluster_portrait",
    )
    def portrait_discover_dimensions(self, request, *args, **kwargs):
        """MCP 工具：portrait_discover_dimensions。

        参见类 docstring；实际业务实现在 ``PortraitQueryService.discover_dimensions``。
        视图层只做"参数取值 + 转发"，db_type 由 Service 通过 (bk_biz_id, cluster_domain) 反查得到。
        """
        bk_biz_id: int = int(self.get_param("bk_biz_id"))
        cluster_domain: str = self.get_param("cluster_domain")
        return Response(
            PortraitQueryService.discover_dimensions(
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "集群画像 - 拉取维度摘要：按 (bk_biz_id, cluster_domain) 批量取指定维度 codes 在时间窗内的"
                "巡检摘要记录（每条含 score 分数，未上报为 null）。返回条数由各维度在注册表中的 "
                "summary_fetch_strategy 决定：all 返回时间窗内全部记录；last 返回最新一条；"
                "first 返回最老一条。codes 不传时默认取该集群 db_type 下所有启用维度。"
            )
        ),
        request_slz=PortraitFetchSummariesInputSerializer,
        response_slz=PortraitFetchSummariesOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.CLUSTER_PORTRAIT],
        name_prefix="cluster_portrait",
    )
    def portrait_fetch_summaries(self, request, *args, **kwargs):
        """MCP 工具：portrait_fetch_summaries。

        参见类 docstring；实际业务实现在 ``PortraitQueryService.fetch_summaries``。
        """
        bk_biz_id: int = int(self.get_param("bk_biz_id"))
        cluster_domain: str = self.get_param("cluster_domain")
        # MCP 入参键名为 dimension_codes（避开框架保留字段 code），Service 内部形参仍是 codes
        codes = self.get_param("dimension_codes", None)
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

    @mcp_tools_api_decorator(
        description=str(
            _(
                "集群画像 - 上报维度巡检摘要：写入一条 (集群, 维度) 的单次巡检摘要，"
                "作为 Agent 生成画像报告的数据源。db_type 由服务端通过 (bk_biz_id, cluster_domain) "
                "反查集群元数据自动得到，无需调用方传入；dimension_code 须为该集群 db_type 下"
                "已定义的维度枚举 value；score 为该条摘要的分数（可选，数值类型，未上报传 null）。"
                "首次上报会自动懒注册到维度注册表。可预期失败通过 status 字段返回，不抛异常。"
            )
        ),
        request_slz=PortraitIngestSummaryInputSerializer,
        response_slz=PortraitIngestSummaryOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.CLUSTER_PORTRAIT],
        name_prefix="cluster_portrait",
    )
    def portrait_ingest_summary(self, request, *args, **kwargs):
        """MCP 工具：portrait_ingest_summary。

        参见类 docstring；实际业务实现在 ``PortraitIngestService.ingest_summary``。
        视图层只做"参数取值 + 转发"，可预期失败由 Service 归一化为 status 字段。
        db_type 不再由入参承载，由 Service 内部通过集群元数据反查得到。
        """
        # MCP 入参键名为 dimension_code（避开框架保留字段 code），Service 内部形参仍是 code
        code: str = self.get_param("dimension_code")
        bk_biz_id: int = int(self.get_param("bk_biz_id"))
        cluster_domain: str = self.get_param("cluster_domain")
        report_time = self.get_param("report_time")
        summary: str = self.get_param("summary", "") or ""
        detail_url: str = self.get_param("detail_url", "") or ""
        score = self.get_param("score", None)
        return Response(
            PortraitIngestService.ingest_summary(
                code=code,
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
                report_time=report_time,
                summary=summary,
                detail_url=detail_url,
                score=score,
            )
        )
