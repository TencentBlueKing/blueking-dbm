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
from backend.db_report.models import AffinityCheckReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin

logger = logging.getLogger("root")


MYSQL_AFFINITY_CHECK_TITLE = [
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
        "name": "region",
        "display_name": _("地域"),
        "format": ReportFieldFormat.TEXT.value,
    },
    {
        "name": "affinity_type",
        "display_name": _("亲和性类型"),
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
]


class MySQLAffinityCheckReportSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    class Meta:
        model = AffinityCheckReport
        fields = (
            "bk_biz_id",
            "dba",
            "cluster",
            "cluster_type",
            "region",
            "affinity_type",
            "state",
            "status",
            "msg",
            "create_at",
            "failed_days",
        )
        swagger_schema_fields = {"example": mock_data.REDIS_META_CHECK_DATA}


class MySQLAffinityCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = AffinityCheckReport.objects.all()
    serializer_class = MySQLAffinityCheckReportSerializer
    report_title = MYSQL_AFFINITY_CHECK_TITLE
    ordering = ["-create_at", "failed_days"]
    filter_fields = {
        "bk_biz_id": ["exact"],
        "cluster_type": ["exact", "in"],
        "region": ["exact"],
        "affinity_type": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
        "state": ["exact", "in"],
        "failed_days": ["exact", "lte", "gte"],
    }

    @common_swagger_auto_schema(
        operation_summary=_("MySQL 亲和性检查"),
        responses={status.HTTP_200_OK: MySQLAffinityCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@register_report(DBType.MySQL)
class MySQLAffinityCheckReportViewSet(MySQLAffinityCheckReportBaseViewSet):
    """TenDBHA 集群亲和性检查报告"""

    queryset = AffinityCheckReport.objects.filter(cluster_type=ClusterType.TenDBHA.value).order_by("-create_at")
    report_type = ReportType.AFFINITY_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("TenDBHA 亲和性检查报告"),
        responses={status.HTTP_200_OK: MySQLAffinityCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
