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
from backend.db_report.models import DbmonHeartbeatReport
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class DbmonHeartbeatCheckReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DbmonHeartbeatReport
        fields = ("bk_biz_id", "cluster", "cluster_type", "app", "dba", "instance", "create_at")
        swagger_schema_fields = {"example": mock_data.DBMON_HEARTBEAT_CHECK_DATA}


class DbmonHeatbeartCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = DbmonHeartbeatReport.objects.all()
    serializer_class = DbmonHeartbeatCheckReportSerializer
    filter_fields = {  # 大部分时候不需要覆盖默认的filter
        "bk_biz_id": ["exact"],
        "cluster_type": ["exact", "in"],
        "cluster": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
    }
    report_name = _("dbmon心跳超时检查")
    report_title = [
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
            "display_name": _("类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "app",
            "display_name": _("业务名"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "dba",
            "display_name": _("业务所属dba"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "instance",
            "display_name": _("实例节点信息"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "create_at",
            "display_name": _("心跳超时时间"),
            "format": ReportFieldFormat.TEXT.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("dbmon心跳超时检查报告"),
        responses={status.HTTP_200_OK: DbmonHeartbeatCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        logger.info("list")
        return super().list(request, *args, **kwargs)
