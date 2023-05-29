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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_report import mock_data
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat
from backend.db_report.models import ChecksumCheckReport
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class ChecksumCheckReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecksumCheckReport
        fields = ("bk_biz_id", "cluster", "status", "fail_slaves", "msg", "id", "create_at")
        swagger_schema_fields = {"example": mock_data.CHECKSUM_CHECK_DATA}


class ChecksumCheckReportViewSet(ReportBaseViewSet):
    queryset = ChecksumCheckReport.objects.all().order_by("-create_at")
    serializer_class = ChecksumCheckReportSerializer
    filter_fields = {
        "bk_biz_id": ["exact"],
        "cluster_type": ["exact"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
        "cluster": ["exact", "in"],
    }
    report_name = _("数据校验")
    report_title = [
        {
            "name": "id",
            "display_name": _("报告ID"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster",
            "display_name": _("集群"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "status",
            "display_name": _("校验结果"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "fail_slaves",
            "display_name": _("失败的从库实例数量"),
            "format": ReportFieldFormat.FAIL_SLAVE_INSTANCE.value,
        },
        {
            "name": "msg",
            "display_name": _("失败信息"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "create_at",
            "display_name": _("时间"),
            "format": ReportFieldFormat.TEXT.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("数据校验"),
        responses={status.HTTP_200_OK: ChecksumCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
