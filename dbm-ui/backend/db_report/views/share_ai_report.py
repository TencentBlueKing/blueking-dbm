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
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_report.models.ai_analysis_report import AiAnalysisReport
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.exceptions import AppBaseException

logger = logging.getLogger("root")
SWAGGER_TAG = _("AI文件报告")


class ClusterHealthReportQuerySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    date = serializers.CharField(help_text=_("报告日期，格式：YYYY-MM-DD"))

    def validate_date(self, value):
        if not parse_date(value):
            raise serializers.ValidationError(_("日期格式错误，请使用 YYYY-MM-DD"))
        return value


class AiReportViewSet(SystemViewSet):
    default_permission_class = []

    @staticmethod
    def _serialize_ai_report(report):
        return {
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

    @common_swagger_auto_schema(
        operation_summary=_("获取集群健康报告"),
        query_serializer=ClusterHealthReportQuerySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, url_path="cluster_health_report")
    def cluster_health_report(self, request):
        params = self.params_validate(ClusterHealthReportQuerySerializer)
        report_date = parse_date(params["date"])
        start_time = timezone.make_aware(datetime.combine(report_date, time.min))
        end_time = start_time + timedelta(days=1)
        portrait_report = (
            ClusterPortraitReport.objects.filter(
                bk_biz_id=params["bk_biz_id"],
                cluster_domain=params["cluster_domain"],
                report_to_time__gte=start_time,
                report_to_time__lt=end_time,
            )
            .exclude(share_url="")
            .order_by("-report_to_time", "-id")
            .first()
        )
        if not portrait_report:
            raise AppBaseException(_("未查询到对应日期的集群健康报告"))

        share_path = portrait_report.share_url.rstrip("/")
        report_id = share_path.rsplit("/", 1)[-1] if share_path else ""
        if not report_id:
            raise AppBaseException(_("集群健康报告分享链接格式错误，无法提取报告 ID"))

        ai_report = AiAnalysisReport.objects.filter(id=report_id).first()
        if not ai_report:
            raise AppBaseException(_("未查询到对应的 AI 分析报告"))

        return Response(
            {
                "portrait_report_id": portrait_report.id,
                "share_url": portrait_report.share_url,
                "report_to_time": portrait_report.report_to_time,
                **self._serialize_ai_report(ai_report),
            }
        )

    @common_swagger_auto_schema(
        operation_summary=_("AI 对话内容分享链接"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, url_path="share/(?P<report_id>[^/.]+)")
    def share(self, request, report_id):
        report = AiAnalysisReport.objects.filter(id=report_id).first()
        if not report:
            raise AppBaseException(_("未查到相关报告, 请检查报告id是否正确"))

        return Response(self._serialize_ai_report(report))
