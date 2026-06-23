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

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_report.models.ai_analysis_report import AiAnalysisReport
from backend.exceptions import AppBaseException

logger = logging.getLogger("root")
SWAGGER_TAG = _("AI文件报告")


class AiReportViewSet(SystemViewSet):
    default_permission_class = []

    @common_swagger_auto_schema(
        operation_summary=_("AI 对话内容分享链接"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, url_path="share/(?P<report_id>[^/.]+)")
    def share(self, request, report_id):
        report = AiAnalysisReport.objects.filter(id=report_id).first()
        if not report:
            raise AppBaseException(_("未查到相关报告, 请检查报告id是否正确"))

        report_data = {
            "report_id": str(report.id),
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
        }

        return Response(report_data)
