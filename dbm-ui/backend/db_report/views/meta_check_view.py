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
from backend.db_report import mock_data
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat
from backend.db_report.models import MetaCheckReport
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin

logger = logging.getLogger("root")


class MetaCheckReportSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    class Meta:
        model = MetaCheckReport
        fields = ("bk_biz_id", "ip", "port", "machine_type", "status", "msg", "create_at", "dba")
        swagger_schema_fields = {"example": mock_data.META_CHECK_DATA}


class MetaCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = MetaCheckReport.objects.all()
    serializer_class = MetaCheckReportSerializer
    report_name = _("元数据检查")
    report_title = [
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
            "name": "ip",
            "display_name": _("IP"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "port",
            "display_name": _("端口"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "machine_type",
            "display_name": _("实例类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "status",
            "display_name": _("元数据状态"),
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
    ]

    @common_swagger_auto_schema(
        operation_summary=_("元数据检查报告列表"),
        responses={status.HTTP_200_OK: MetaCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
