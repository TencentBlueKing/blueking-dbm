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
from backend.db_report.enums import SWAGGER_TAG, MysqlBackupCheckSubType, ReportFieldFormat, ReportType
from backend.db_report.models import MysqlBackupCheckReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin

logger = logging.getLogger("root")


class MysqlBackupCheckReportSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    class Meta:
        model = MysqlBackupCheckReport
        fields = ("bk_biz_id", "cluster", "cluster_type", "status", "msg", "create_at", "dba")
        swagger_schema_fields = {"example": mock_data.MYSQL_BACKUP_CHECK_DATA}


class MysqlBackupCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = MysqlBackupCheckReport.objects.all()
    serializer_class = MysqlBackupCheckReportSerializer
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
            "display_name": _("集群类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "status",
            "display_name": _("全备状态"),
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
        operation_summary=_("备份检查报告"),
        responses={status.HTTP_200_OK: MysqlBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        logger.info("list")
        return super().list(request, *args, **kwargs)


@register_report(DBType.MySQL)
class MysqlFullBackupCheckReportViewSet(MysqlBackupCheckReportBaseViewSet):
    cluster_types = ClusterType.db_type_to_cluster_types(DBType.MySQL)
    queryset = MysqlBackupCheckReport.objects.filter(
        subtype=MysqlBackupCheckSubType.FullBackup.value, cluster_type__in=cluster_types
    )
    serializer_class = MysqlBackupCheckReportSerializer
    report_type = ReportType.FULL_BACKUP_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("全备检查报告"),
        responses={status.HTTP_200_OK: MysqlBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@register_report(DBType.MySQL)
class MysqlBinlogBackupCheckReportViewSet(MysqlBackupCheckReportBaseViewSet):
    cluster_types = ClusterType.db_type_to_cluster_types(DBType.MySQL)
    queryset = MysqlBackupCheckReport.objects.filter(
        subtype=MysqlBackupCheckSubType.BinlogSeq.value, cluster_type__in=cluster_types
    )
    serializer_class = MysqlBackupCheckReportSerializer
    report_type = ReportType.BINLOG_BACKUP_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("binlog检查报告"),
        responses={status.HTTP_200_OK: MysqlBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
