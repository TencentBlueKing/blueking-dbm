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
from backend.db_periodic_task.models import MySQLBackupRecoverTask
from backend.db_report import mock_data
from backend.db_report.enums import DrillFilterType, ReportFieldFormat, ReportType
from backend.db_report.report_baseview import BaseDrillReportViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin
from backend.env import BK_SAAS_HOST, MYSQL_BACKUPRECOVER_BIZ_ID

logger = logging.getLogger("root")
SWAGGER_TAG = _("演练报告")


class BackupRecoverTaskSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    """回档演练任务序列化器"""

    recover_duration = serializers.SerializerMethodField(help_text=_("恢复花费时间(小时)"))
    task_id = serializers.SerializerMethodField(help_text=_("任务ID链接"))

    def get_recover_duration(self, obj):
        """计算恢复花费时间"""
        if obj.recover_start_time and obj.recover_end_time:
            duration = obj.recover_end_time - obj.recover_start_time
            return round(duration.total_seconds() / 3600, 2)  # 转换为小时，保留两位小数
        return None

    def get_task_id(self, obj):
        """生成任务ID的超链接"""
        if not obj.task_id:
            return None
        return f"{BK_SAAS_HOST}/{MYSQL_BACKUPRECOVER_BIZ_ID}/task-history/detail/{obj.task_id}?from=taskHistoryList"

    class Meta:
        model = MySQLBackupRecoverTask
        fields = (
            "bk_biz_id",
            "dba",
            "cluster_type",
            "cluster_domain",
            "backup_begin_time",
            "backup_total_size",
            "recover_duration",
            "status",
            "state",
            "task_id",
            "task_info",
            "charset",
            "mysql_version",
            "backup_type",
            "backup_tool",
            "create_at",
        )
        swagger_schema_fields = {"example": mock_data.REPORT_BACKUP_RECOVER_DATA}


class RecoverDrillTaskViewSet(BaseDrillReportViewSet):
    """回档演练任务视图集"""

    # TODO: 挪库后 MySQLBackupRecoverTask 应该修改为 BaseModel 类
    queryset = MySQLBackupRecoverTask.objects.all()
    serializer_class = BackupRecoverTaskSerializer

    filter_fields = {
        "bk_biz_id": ["exact", "in"],
        "cluster_domain": ["exact", "in"],
        "cluster_type": ["exact", "in"],
        "state": ["exact", "in"],
        "create_at": ["gte", "lte"],
    }
    ordering_fields = ["backup_begin_time", "recover_duration", "create_at", "failed_days"]

    report_type = ReportType.BACKUP_RECOVER_DRILL
    report_title = [
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.BIZ},
        },
        {
            "name": "dba",
            "display_name": _("DBA"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_type",
            "display_name": _("架构类型"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_domain",
            "display_name": _("域名"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "mysql_version",
            "display_name": _("MySQL版本"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "charset",
            "display_name": _("备份字符集"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "backup_type",
            "display_name": _("备份类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "backup_tool",
            "display_name": _("备份工具"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "backup_total_size",
            "display_name": _("备份大小"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "backup_begin_time",
            "display_name": _("备份开始时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "recover_duration",
            "display_name": _("恢复花费时间(小时)"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "status",
            "display_name": _("任务状态"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "create_at",
            "display_name": _("任务创建时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "task_id",
            "display_name": _("任务链接"),
            "format": ReportFieldFormat.LINK.value,
        },
        {
            "name": "task_info",
            "display_name": _("任务信息"),
            "format": ReportFieldFormat.LOG.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("回档演练报告"),
        responses={status.HTTP_200_OK: BackupRecoverTaskSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
