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
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report import mock_data
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat, ReportType
from backend.db_report.models.mysql_exporter_check_report import MysqlExporterCheckReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin

logger = logging.getLogger("root")


MYSQL_EXPORTER_CHECK_TITLE = [
    {
        "name": "bk_biz_id",
        "display_name": _("业务"),
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
        "name": "instance",
        "display_name": _("实例地址"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "subtype",
        "display_name": _("检查子类型"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "state",
        "display_name": _("检查状态"),
        "format": ReportFieldFormat.STATUS.value,
    },
    {
        "name": "msg",
        "display_name": _("详情"),
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
    {
        "name": "dba",
        "display_name": _("DBA"),
        "format": ReportFieldFormat.TEXT.value,
    },
]


class MySQLExporterCheckReportSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    class Meta:
        model = MysqlExporterCheckReport
        fields = (
            "bk_biz_id",
            "dba",
            "cluster",
            "cluster_type",
            "instance",
            "subtype",
            "state",
            "msg",
            "create_at",
            "failed_days",
        )
        swagger_schema_fields = {"example": mock_data.REDIS_META_CHECK_DATA}


class MySQLExporterCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = MysqlExporterCheckReport.objects.all()
    serializer_class = MySQLExporterCheckReportSerializer
    report_title = MYSQL_EXPORTER_CHECK_TITLE

    @common_swagger_auto_schema(
        operation_summary=_("MySQL Exporter 巡检报告"),
        responses={status.HTTP_200_OK: MySQLExporterCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@register_report(DBType.MySQL)
class MySQLExporterCheckReportViewSet(MySQLExporterCheckReportBaseViewSet):
    """TenDBHA Exporter 巡检报告"""

    queryset = MysqlExporterCheckReport.objects.filter(cluster_type=ClusterType.TenDBHA.value).order_by("-create_at")
    report_type = ReportType.EXPORTER_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("TenDBHA Exporter 巡检报告"),
        responses={status.HTTP_200_OK: MySQLExporterCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
