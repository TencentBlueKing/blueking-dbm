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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import MysqlBackupCheckSubType, ReportType
from backend.db_report.models import MysqlBackupCheckReport
from backend.db_report.register import register_report
from backend.db_report.views.mysql.mysqlbackup_check_view import (
    MysqlBinlogBackupCheckReportViewSet,
    MysqlFullBackupCheckReportViewSet,
)

logger = logging.getLogger("root")


@register_report(DBType.TenDBCluster)
class TendbClusterFullBackupCheckReportViewSet(MysqlFullBackupCheckReportViewSet):
    queryset = MysqlBackupCheckReport.objects.filter(
        subtype=MysqlBackupCheckSubType.FullBackup.value, cluster_type=ClusterType.TenDBCluster
    )
    report_type = ReportType.FULL_BACKUP_CHECK


@register_report(DBType.TenDBCluster)
class TendbClusterBackupCheckReportViewSet(MysqlBinlogBackupCheckReportViewSet):
    queryset = MysqlBackupCheckReport.objects.filter(
        subtype=MysqlBackupCheckSubType.BinlogSeq.value, cluster_type=ClusterType.TenDBCluster
    )
    report_type = ReportType.BINLOG_BACKUP_CHECK
