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
from django.utils.translation import gettext as _
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import SWAGGER_TAG, MysqlConfigConsistencySubType, ReportFieldFormat, ReportType
from backend.db_report.models import MysqlConfigConsistencyReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin

# 周频巡检：列表、状态统计与待办角标统一兜底至少近 7 天窗口
DEFAULT_WEEKLY_LOOKBACK_DAYS = 7

MYSQL_CONFIG_CONSISTENCY_TITLE = [
    {
        "name": "bk_biz_id",
        "display_name": _("业务"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "dba",
        "display_name": _("DBA"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "cluster",
        "display_name": _("集群域名"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "cluster_type",
        "display_name": _("集群类型"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "state",
        "display_name": _("检查状态"),
        "format": ReportFieldFormat.STATUS.value,
    },
    {
        "name": "diff_variables",
        "display_name": _("差异配置项"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "msg",
        "display_name": _("差异详情"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "create_at",
        "display_name": _("巡检时间"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "failed_days",
        "display_name": _("持续天数"),
        "format": ReportFieldFormat.TEXT.value,
    },
]

TENDBCLUSTER_CONFIG_CONSISTENCY_TITLE = [
    *MYSQL_CONFIG_CONSISTENCY_TITLE[:4],
    {
        "name": "subtype_display",
        "display_name": _("检查项"),
        "format": ReportFieldFormat.TEXT.value,
    },
    *MYSQL_CONFIG_CONSISTENCY_TITLE[4:],
]


class MysqlConfigConsistencyReportSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    subtype_display = serializers.SerializerMethodField(help_text=_("检查项名称"))

    def get_subtype_display(self, obj) -> str:
        return str(MysqlConfigConsistencySubType.get_choice_label(obj.subtype) or obj.subtype)

    class Meta:
        model = MysqlConfigConsistencyReport
        fields = (
            "bk_biz_id",
            "dba",
            "cluster",
            "cluster_type",
            "subtype",
            "subtype_display",
            "state",
            "status",
            "diff_count",
            "high_impact_count",
            "diff_variables",
            "msg",
            "create_at",
            "failed_days",
        )


class MysqlConfigConsistencyReportBaseViewSet(ReportBaseViewSet):
    queryset = MysqlConfigConsistencyReport.objects.all()
    serializer_class = MysqlConfigConsistencyReportSerializer
    report_title = MYSQL_CONFIG_CONSISTENCY_TITLE
    min_time_range_days = DEFAULT_WEEKLY_LOOKBACK_DAYS
    ordering = ["-create_at", "failed_days"]
    filter_fields = {
        "bk_biz_id": ["exact"],
        "cluster_type": ["exact", "in"],
        "subtype": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
        "state": ["exact", "in"],
        "failed_days": ["exact", "lte", "gte"],
    }

    @common_swagger_auto_schema(
        operation_summary=_("配置一致性巡检"),
        responses={status.HTTP_200_OK: MysqlConfigConsistencyReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@register_report(DBType.MySQL)
class MysqlConfigConsistencyReportViewSet(MysqlConfigConsistencyReportBaseViewSet):
    """TenDBHA 主从关键配置一致性巡检报告"""

    queryset = MysqlConfigConsistencyReport.objects.filter(cluster_type=ClusterType.TenDBHA.value).order_by(
        "-create_at"
    )
    report_type = ReportType.CONFIG_CONSISTENCY_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("MySQL 主从关键配置一致性巡检"),
        responses={status.HTTP_200_OK: MysqlConfigConsistencyReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
