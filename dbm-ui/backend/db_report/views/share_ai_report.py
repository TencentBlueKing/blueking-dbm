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
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.ai_analysis_report import AiAnalysisReport
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.db_report.models.portrait_dimension_registry import PortraitDimensionRegistry
from backend.exceptions import AppBaseException
from blue_krill.data_types.enum import EnumField, StrStructuredEnum

logger = logging.getLogger("root")
SWAGGER_TAG = _("AI文件报告")


class ClusterHealthReportQuerySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    date = serializers.CharField(required=False, allow_blank=True, help_text=_("报告日期，格式：YYYY-MM-DD"))

    def validate_date(self, value):
        if value and not parse_date(value):
            raise serializers.ValidationError(_("日期格式错误，请使用 YYYY-MM-DD"))
        return value


class ClusterHealthReportStatus(StrStructuredEnum):
    NOT_CONNECTED = EnumField("not_connected", _("未接入报告"))
    NOT_GENERATED = EnumField("not_generated", _("已接入报告但未产生报告"))
    GENERATED = EnumField("generated", _("已产生报告"))


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
        def get_cluster_db_type(cluster_type):
            # 集群表存的是 cluster_type，画像维度注册表按 db_type 接入，需要先做一次映射。
            for db_type, cluster_types in ClusterType.db_type_cluster_types_map().items():
                if cluster_type in [candidate.value for candidate in cluster_types]:
                    return db_type
            return ""

        def serialize_cluster_health_report(portrait_report, ai_report):
            return {
                "portrait_report_id": portrait_report.id,
                "share_url": portrait_report.share_url,
                "report_to_time": portrait_report.report_to_time,
                **self._serialize_ai_report(ai_report),
            }

        def get_available_dates(qs):
            return list(
                dict.fromkeys(
                    timezone.localtime(report_time).date().isoformat()
                    for report_time in qs.values_list("report_to_time", flat=True)
                )
            )

        def empty_cluster_health_report(report_status: ClusterHealthReportStatus, available_dates=None):
            return Response(
                {
                    "report_status": report_status.value,
                    "has_report": False,
                    "available_dates": available_dates or [],
                }
            )

        params = self.params_validate(ClusterHealthReportQuerySerializer)
        cluster = Cluster.objects.filter(
            bk_biz_id=params["bk_biz_id"],
            immute_domain=params["cluster_domain"],
        ).first()
        cluster_db_type = get_cluster_db_type(cluster.cluster_type) if cluster else ""
        # 注册表里没有该 db_type 的维度，表示当前类型的集群画像报告还未接入。
        if not cluster_db_type or not PortraitDimensionRegistry.objects.filter(db_type=cluster_db_type).exists():
            return empty_cluster_health_report(ClusterHealthReportStatus.NOT_CONNECTED)

        # 同一个域名可能被重建复用，过滤掉早于当前集群创建时间的历史报告。
        base_qs = ClusterPortraitReport.objects.filter(
            bk_biz_id=params["bk_biz_id"],
            cluster_domain=params["cluster_domain"],
            report_to_time__gte=cluster.create_at,
        ).exclude(share_url="")
        available_dates = get_available_dates(base_qs)
        latest_portrait_report = base_qs.order_by("-report_to_time", "-id").first()
        report_date = parse_date(params.get("date") or "") or (
            timezone.localtime(latest_portrait_report.report_to_time).date() if latest_portrait_report else None
        )
        if not report_date:
            return empty_cluster_health_report(ClusterHealthReportStatus.NOT_GENERATED, available_dates)
        start_time = timezone.make_aware(datetime.combine(report_date, time.min))
        end_time = start_time + timedelta(days=1)
        portrait_report = (
            base_qs.filter(
                report_to_time__gte=start_time,
                report_to_time__lt=end_time,
            )
            .order_by("-report_to_time", "-id")
            .first()
        )

        # 已接入画像能力，但所选日期当天没有生成可用报告。
        if not portrait_report:
            return empty_cluster_health_report(ClusterHealthReportStatus.NOT_GENERATED, available_dates)

        share_path = portrait_report.share_url.rstrip("/")
        report_id = share_path.rsplit("/", 1)[-1] if share_path else ""
        # 画像记录存在但分享链接格式异常，按“未产生可用报告”处理，避免前端收到异常。
        if not report_id:
            return empty_cluster_health_report(ClusterHealthReportStatus.NOT_GENERATED, available_dates)

        ai_report = AiAnalysisReport.objects.filter(id=report_id).first()
        # 分享链接指向的 AI 报告不存在，说明当天报告不可用。
        if not ai_report:
            return empty_cluster_health_report(ClusterHealthReportStatus.NOT_GENERATED, available_dates)

        return Response(
            {
                "report_status": ClusterHealthReportStatus.GENERATED.value,
                "has_report": True,
                "available_dates": available_dates,
                **serialize_cluster_health_report(portrait_report, ai_report),
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
