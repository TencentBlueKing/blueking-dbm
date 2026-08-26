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
import os
import struct
import zlib

from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from backend import env
from backend.db_report.models.ai_analysis_report import AiAnalysisReport
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs
from backend.dbm_aiagent.mcp_tools.common.serializers.ai_report import (
    ReadAiReportInputSerializer,
    ReadAiReportOutputSerializer,
    WriteAiReportInputSerializer,
    WriteAiReportOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.mcp import McpDBManagePermission

logger = logging.getLogger("root")


def validate_content_not_filepath(content: str):
    """校验 content 不是文件路径。如果大模型只传了文件名而没有传文件内容，这是无意义的。"""
    if (
        content.startswith("/")
        or content.startswith("./")
        or content.startswith("~/")
        or (len(content.splitlines()) == 1 and "." in os.path.basename(content) and len(content) < 260)
    ):
        raise ValidationError(_("content 参数内容不能是文件路径，如果是 dbm-mcp-cli/mcporter 工具调用, 路径前需要 @ 符号"))


class AiReportMcpToolsViewSet(McpToolsViewSet):
    @mcp_tools_api_decorator(
        description=str(_("写入 AI 分析报告。将 AI Agent 的分析结果持久化存储，支持 markdown 和 html 格式。")),
        request_slz=WriteAiReportInputSerializer,
        response_slz=WriteAiReportOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        mcp=[DBMMcpTools.AI_REPORT],
        name_prefix="ai_report",
    )
    def write_report(self, request, *args, **kwargs):
        ai_agent = self.get_param("ai_agent")
        result_format = self.get_param("format")
        bk_biz_id = self.get_param("bk_biz_id", 0)
        cluster_domain = self.get_param("cluster_domain", "")
        title = self.get_param("title", "")
        summary = self.get_param("summary", "")
        content = self.get_param("content")
        validate_content_not_filepath(content)

        # 获取当前用户作为创建者
        creator = request.user.username if hasattr(request, "user") and request.user else ""

        # 使用 zlib 压缩 content 后存储（兼容 MySQL UNCOMPRESS() 格式：4字节小端序原始长度 + zlib 数据）
        content_bytes = content.encode("utf-8")
        compressed_content = struct.pack("<I", len(content_bytes)) + zlib.compress(content_bytes)

        report = AiAnalysisReport.objects.create(
            ai_agent=ai_agent,
            format=result_format,
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            title=title,
            summary=summary,
            content=compressed_content,
            creator=creator,
        )

        return Response(
            {
                "report_id": str(report.id),
                "bk_biz_id": report.bk_biz_id,
                "share_url": f"{env.BK_SAAS_HOST}/ai-chat/share/{str(report.id)}/",
                "message": _("报告写入成功"),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("读取 AI 分析报告。支持按报告 ID 精确查询，或按 ai_agent、bk_biz_id、cluster_domain 等条件过滤查询。")),
        request_slz=ReadAiReportInputSerializer,
        response_slz=ReadAiReportOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        mcp=[DBMMcpTools.AI_REPORT],
        name_prefix="ai_report",
    )
    def read_report(self, request, *args, **kwargs):
        report_id = self.get_param("report_id")
        bk_biz_id = self.get_param("bk_biz_id")

        try:
            report = AiAnalysisReport.objects.get(id=report_id, bk_biz_id=bk_biz_id)
        except AiAnalysisReport.DoesNotExist:
            return Response({"message": f"报告 {report_id} 不存在"}, status=Http404)

        report_data = {
            "id": str(report.id),
            "ai_agent": report.ai_agent,
            "format": report.format,
            "bk_biz_id": report.bk_biz_id,
            "cluster_domain": report.cluster_domain,
            "title": report.title,
            "summary": report.summary,
            "content": report.get_content(),
            "creator": report.creator,
            "create_at": report.create_at,
            "update_at": report.update_at,
            "share_url": f"{env.BK_SAAS_HOST}/ai-chat/share/{str(report.id)}/",
        }

        return Response({"report": report_data})
