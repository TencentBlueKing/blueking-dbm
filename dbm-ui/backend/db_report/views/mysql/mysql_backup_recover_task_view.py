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
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase
from backend.db_report.register import register_drill_report
from backend.db_report.views.revover_drill_report_view import RecoverDrillTaskViewSet

logger = logging.getLogger("root")


@register_drill_report(DBType.MySQL)
class MySQLBackupRecoverTaskViewSet(RecoverDrillTaskViewSet):
    """MySQL备份恢复任务视图集"""

    queryset = MySQLBackupRecoverTask.objects.filter(phase=TaskPhase.DONE, cluster_type=ClusterType.TenDBHA).order_by(
        "-create_at"
    )


@register_drill_report(DBType.TenDBCluster)
class TendbClusterBackupRecoverTaskViewSet(RecoverDrillTaskViewSet):
    """TendbCluster备份恢复演练任务视图集"""

    queryset = MySQLBackupRecoverTask.objects.filter(
        phase=TaskPhase.DONE, cluster_type=ClusterType.TenDBCluster
    ).order_by("-create_at")
