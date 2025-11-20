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
from backend.db_report import mock_data
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat, ReportType
from backend.db_report.models.es_account_report import EsAccountReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class EsAccountReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = EsAccountReport
        fields = ("bk_biz_id", "app", "domain", "dba", "cluster_type", "create_at", "msg", "state", "have_admin")
        swagger_schema_fields = {"example": mock_data.ES_ACCOUNT_CHECK_DATA}


@register_report(DBType.Es)
class EsAccountReportBaseViewSet(ReportBaseViewSet):
    queryset = EsAccountReport.objects.all().order_by("-create_at", "state")
    serializer_class = EsAccountReportSerializer
    report_type = ReportType.ES_ACCOUNT_CHECK
    report_title = [
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "app",
            "display_name": _("业务名"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "domain",
            "display_name": _("集群域名"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster_type",
            "display_name": _("集群类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "dba",
            "display_name": _("业务所属dba"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "create_at",
            "display_name": _("巡检时间"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {"name": "msg", "display_name": _("检查结果"), "format": ReportFieldFormat.TEXT.value},
        {
            "name": "state",
            "display_name": _("检查状态"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "have_admin",
            "display_name": _("拥有ADMIN账号"),
            "format": ReportFieldFormat.TEXT.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("es集群版本巡检报告"),
        responses={status.HTTP_200_OK: EsAccountReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        logger.info("list")
        return super().list(request, *args, **kwargs)
