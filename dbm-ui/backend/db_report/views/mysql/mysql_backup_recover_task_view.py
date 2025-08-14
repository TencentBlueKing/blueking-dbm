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
from rest_framework import status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_periodic_task.models import MySQLBackupRecoverTask
from backend.db_report.enums import SWAGGER_TAG, ReportFieldFormat, ReportType
from backend.db_report.register import register_report
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.serializers import MySQLBackupRecoverTaskSerializer

logger = logging.getLogger("root")


@register_report(DBType.MySQL)
class MySQLBackupRecoverTaskViewSet(ReportBaseViewSet):
    """MySQL备份恢复任务视图集"""

    queryset = MySQLBackupRecoverTask.objects.all().order_by("-create_at")
    serializer_class = MySQLBackupRecoverTaskSerializer
    report_type = ReportType.MYSQL_BACKUP_RECOVER_TASK
    report_name = _("MySQL备份恢复任务")
    report_title = [
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster_domain",
            "display_name": _("集群名称"),
            "format": ReportFieldFormat.TEXT.value,
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
            "name": "backup_begin_time",
            "display_name": _("备份开始时间"),
            "format": ReportFieldFormat.TEXT.value,
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
            "name": "task_id",
            "display_name": _("任务ID"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "create_at",
            "display_name": _("任务创建时间"),
            "format": ReportFieldFormat.TEXT.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("MySQL备份恢复任务列表"),
        responses={status.HTTP_200_OK: MySQLBackupRecoverTaskSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
