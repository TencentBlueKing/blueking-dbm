# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_report import mock_data
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat, ReportType
from backend.db_report.models import KafkaDiskGrowthReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class KafkaDiskGrowthReportSerializer(serializers.ModelSerializer):
    swagger_schema_fields = {"example": mock_data.KAFKA_DISK_GROWTH_CHECK_DATA}

    # 表格里展示成可读的文本：规则/状态用中文名，日峰值序列用箭头连起来
    rule = serializers.CharField(source="get_rule_display", read_only=True)
    ai_status = serializers.CharField(source="get_ai_status_display", read_only=True)
    peaks = serializers.SerializerMethodField()

    class Meta:
        model = KafkaDiskGrowthReport
        fields = (
            "bk_biz_id",
            "app",
            "domain",
            "dba",
            "create_at",
            "cluster_type",
            "msg",
            "state",
            "failed_days",
            "ip",
            "mount_point",
            "check_day",
            "run_kind",
            "rule",
            "peak",
            "excess",
            "daily_growth",
            "peaks",
            "retention_hours",
            "ai_status",
            "ai_analysis",
        )

    @staticmethod
    def get_peaks(obj) -> str:
        return " → ".join(str(point.get("peak")) for point in obj.peaks or [])


@register_report(DBType.Kafka)
class KafkaDiskGrowthReportBaseViewSet(ReportBaseViewSet):
    queryset = KafkaDiskGrowthReport.objects.all().order_by("-create_at", "-peak")
    serializer_class = KafkaDiskGrowthReportSerializer
    report_type = ReportType.KAFKA_DISK_GROWTH_CHECK
    report_title = [
        {"name": "bk_biz_id", "display_name": _("业务"), "format": ReportFieldFormat.TEXT.value},
        {"name": "app", "display_name": _("业务名"), "format": ReportFieldFormat.TEXT.value},
        {"name": "domain", "display_name": _("集群域名"), "format": ReportFieldFormat.TEXT.value},
        {"name": "ip", "display_name": _("Broker IP"), "format": ReportFieldFormat.TEXT.value},
        {"name": "mount_point", "display_name": _("挂载点"), "format": ReportFieldFormat.TEXT.value},
        {"name": "dba", "display_name": _("业务所属dba"), "format": ReportFieldFormat.TEXT.value},
        {"name": "state", "display_name": _("检查状态"), "format": ReportFieldFormat.STATUS.value},
        {"name": "rule", "display_name": _("触发规则"), "format": ReportFieldFormat.TEXT.value},
        {"name": "peak", "display_name": _("当天峰值(%)"), "format": ReportFieldFormat.TEXT.value},
        {"name": "excess", "display_name": _("比此前7天最高值高(点)"), "format": ReportFieldFormat.TEXT.value},
        {"name": "daily_growth", "display_name": _("近3天日均涨幅(点)"), "format": ReportFieldFormat.TEXT.value},
        {"name": "peaks", "display_name": _("最近8天日峰值(%)"), "format": ReportFieldFormat.TEXT.value},
        {"name": "retention_hours", "display_name": _("集群级保留期(小时)"), "format": ReportFieldFormat.TEXT.value},
        {"name": "ai_analysis", "display_name": _("AI分析"), "format": ReportFieldFormat.TEXT.value},
        {"name": "ai_status", "display_name": _("AI分析状态"), "format": ReportFieldFormat.TEXT.value},
        {"name": "check_day", "display_name": _("判定日期"), "format": ReportFieldFormat.TEXT.value},
        {"name": "create_at", "display_name": _("巡检时间"), "format": ReportFieldFormat.TEXT.value},
        {"name": "failed_days", "display_name": _("持续天数"), "format": ReportFieldFormat.TEXT.value},
    ]

    @common_swagger_auto_schema(
        operation_summary=_("Kafka磁盘持续增长巡检报告"),
        responses={status.HTTP_200_OK: KafkaDiskGrowthReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        logger.info("list")
        return super().list(request, *args, **kwargs)
