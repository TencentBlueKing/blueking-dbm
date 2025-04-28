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
from backend.db_report.enums.mongodb_check_sub_type import MongodbBackupCheckSubType, MongodbExporterCheckSubType
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class MongodbBackupCheckReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MongodbBackupCheckReport
        fields = ("bk_biz_id", "cluster", "cluster_type", "instance", "status", "msg", "create_at")
        swagger_schema_fields = {"example": mock_data.MONGODB_BACKUP_CHECK_DATA}


class MongodbBackupCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = MongodbBackupCheckReport.objects.all()
    serializer_class = MongodbBackupCheckReportSerializer
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
            "name": "instance",
            "display_name": _("实例节点"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster_type",
            "display_name": _("集群类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "status",
            "display_name": _("检查结果"),
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
        responses={status.HTTP_200_OK: MongodbBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        logger.info("list")
        return super().list(request, *args, **kwargs)


@register_report(DBType.MongoDB)
class MongodbFullBackupCheckReportViewSet(MongodbBackupCheckReportBaseViewSet):
    queryset = MongodbBackupCheckReport.objects.filter(subtype=MongodbBackupCheckSubType.FullBackup.value)
    serializer_class = MongodbBackupCheckReportSerializer
    report_type = ReportType.FULL_BACKUP_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("MongoDB 全备检查报告"),
        responses={status.HTTP_200_OK: MongodbBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@register_report(DBType.MongoDB)
class MongodbExporterCheckReportViewSet(MongodbBackupCheckReportBaseViewSet):
    queryset = MongodbBackupCheckReport.objects.filter(subtype=MongodbExporterCheckSubType.Up.value)

    serializer_class = MongodbBackupCheckReportSerializer
    report_type = ReportType.EXPORTER_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("MongoDB Exporter检查报告"),
        responses={status.HTTP_200_OK: MongodbBackupCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
