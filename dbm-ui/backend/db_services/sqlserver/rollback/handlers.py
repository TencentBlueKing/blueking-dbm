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

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from backend.components.bklog.handler import BKLogHandler
from backend.db_meta.models import Cluster
from backend.db_services.sqlserver.rollback.constants import BACKUP_LOG_RANGE_DAYS
from backend.exceptions import AppBaseException
from backend.flow.utils.sqlserver.sqlserver_db_function import sqlserver_match_dbs
from backend.utils.time import datetime2str, find_nearby_time, str2datetime, timezone2timestamp


class SQLServerRollbackHandler(object):
    """sqlserver定点构造函数封装"""

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    @staticmethod
    def _get_log_from_bklog(collector: str, start_time: datetime, end_time: datetime, query_string="*") -> List[Dict]:
        return BKLogHandler.query_logs(collector, start_time, end_time, query_string)

    def query_binlogs(self, start_time: datetime, end_time: datetime):
        """
        根据时间范围查询集群的binlog记录
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {self.cluster.id}",
        )
        # TODO: binlog是否需要聚合 or 转义
        return binlogs

    def query_backup_logs(self, start_time: datetime, end_time: datetime):
        """
        根据时间范围查询集群的备份记录
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        backup_logs = self._get_log_from_bklog(
            collector="mssql_dbbackup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {self.cluster.id}",
        )

        # 根据backup id聚合备份记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_logs:
            if log["data_schema_grant"] == "all":
                backup_id__logs[log["backup_id"]].append(log)

        # 对每个聚合记录补充信息
        backup_logs: List[Dict[str, Any]] = []
        for backup_id, logs in backup_id__logs.items():
            start_time = min(map(str2datetime, [log["backup_begin_time"] for log in logs]))
            end_time = max(map(str2datetime, [log["backup_end_time"] for log in logs]))
            backup_log_info = {
                "start_time": datetime2str(start_time),
                "end_time": datetime2str(end_time),
                "backup_id": backup_id,
                "logs": logs,
                # 是否只取第一个log的角色就好了？
                "role": logs[0]["role"],
            }
            backup_logs.append(backup_log_info)

        return backup_logs

    def query_latest_backup_log(self, rollback_time: datetime):
        """
        根据回档时间查询集群最近的备份记录
        @param rollback_time: 回档时间
        """
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = self.query_backup_logs(start_time, end_time)

        # 查询最近的备份记录
        backup_logs.sort(key=lambda x: x["end_time"])
        time_keys = [log["end_time"] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag=1)
        except IndexError:
            raise AppBaseException(_("无法找到时间点{}附近的全备日志记录").format(rollback_time))

        return backup_logs[latest_backup_log_index]

    def query_dbs_by_backup_log(
        self,
        db_pattern: List[str],
        ignore_db: List[str],
        backup_logs: List[Dict] = None,
        rollback_time: datetime = None,
    ):
        """
        根据回档记录/回档时间，和库正则，过滤真正操作的DB库
        @param db_pattern: 库正则
        @param ignore_db: 忽略库正则
        @param backup_logs: 备份记录列表(这里只关注记录中的备份库字段)
        @param rollback_time: 回档时间
        """
        if rollback_time:
            backup_logs = self.query_latest_backup_log(rollback_time)

        db_names = [log["dbname"] for log in backup_logs["logs"]]
        real_db_names = sqlserver_match_dbs(db_names, db_pattern, ignore_db)
        return real_db_names
