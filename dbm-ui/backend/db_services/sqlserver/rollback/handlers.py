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
from typing import Any, Dict, List, Set

from django.utils.translation import gettext as _

from backend.components.bklog.handler import BKLogHandler
from backend.db_meta.models import Cluster
from backend.db_report.models.sqlserver_full_backup_result import SQLServerBackupResult
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.db_services.sqlserver.rollback.constants import BACKUP_LOG_RANGE_DAYS
from backend.flow.utils.sqlserver.sqlserver_db_function import sqlserver_match_dbs
from backend.utils.time import datetime2str, find_nearby_time, str2datetime, timezone2timestamp


class SQLServerRollbackHandler(object):
    """sqlserver定点构造函数封装"""

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    @staticmethod
    def _serialize_backup_log(log: Dict) -> Dict:
        """
        将备份记录中的 datetime 字段转换为字符串，避免 JSON 序列化失败

        @param log: 备份记录字典
        @return: 序列化后的备份记录字典
        """
        serialized_log = log.copy()
        datetime_fields = [
            "created_at",
            "updated_at",
            "backup_task_start_time",
            "backup_task_end_time",
            "backup_begin_time",
            "backup_end_time",
        ]
        for field in datetime_fields:
            if field in serialized_log and serialized_log[field]:
                serialized_log[field] = datetime2str(serialized_log[field])
        return serialized_log

    @staticmethod
    def _get_log_from_bklog(
        collector: str, start_time: datetime, end_time: datetime, query_string="*", size=-1, sort_rule="asc"
    ) -> List[Dict]:
        return BKLogHandler.query_logs(collector, start_time, end_time, query_string, size, sort_rule)

    def query_binlogs(self, start_time: datetime, end_time: datetime, dbname: str):
        """
        根据时间范围查询集群的binlog记录
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        @param dbname: 查询db
        """
        # 单独获取最后一个binlog, 加1秒为了保证获取比时间点大于的日志备份
        last_binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=end_time + timedelta(seconds=1),
            end_time=end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS),
            query_string=f"""cluster_id: {self.cluster.id} AND dbname: "{dbname}" """,
            size=1,
        )
        if not last_binlogs:
            raise ValueError(
                _(
                    "cluster [{}] 在时间范围 [{}~{}] 内找不到后续的日志备份记录".format(
                        self.cluster.name, end_time, end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS)
                    )
                )
            )

        # 然后获取时间范围内的binlog
        binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=start_time,
            end_time=end_time + timedelta(seconds=1),
            query_string=f"""cluster_id: {self.cluster.id} AND dbname: "{dbname}" """,
        )
        # TODO: binlog是否需要聚合 or 转义
        # list去重
        unique_list = []
        seen_values = set()
        for binlog in binlogs + last_binlogs:
            if binlog["backup_id"] not in seen_values:
                unique_list.append(binlog)
                seen_values.add(binlog["backup_id"])

        return unique_list

    def query_binlogs_from_model(self, start_time: datetime, end_time: datetime, dbname: str) -> List[Dict]:
        """
        基于 SQLServerBinlogResult Model 查询集群的 binlog 记录（替代 bklog 查询）
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        @param dbname: 查询 db
        """
        # 单独获取最后一个 binlog，加 1 秒为了保证获取比时间点大于的日志备份
        last_binlog_qs = SQLServerBinlogResult.objects.filter(
            cluster_id=self.cluster.id,
            dbname=dbname,
            backup_end_time__gte=end_time + timedelta(seconds=1),
            backup_end_time__lte=end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS),
        ).order_by("backup_end_time")[:1]

        last_binlogs = list(last_binlog_qs.values())
        if not last_binlogs:
            raise ValueError(
                _(
                    "cluster [{}] 在时间范围 [{}~{}] 内找不到后续的日志备份记录".format(
                        self.cluster.name, end_time, end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS)
                    )
                )
            )

        # 然后获取时间范围内的 binlog
        binlog_qs = SQLServerBinlogResult.objects.filter(
            cluster_id=self.cluster.id,
            dbname=dbname,
            backup_end_time__gte=start_time,
            backup_end_time__lte=end_time + timedelta(seconds=1),
        ).order_by("backup_end_time")

        binlogs = list(binlog_qs.values())

        # list 去重
        unique_list = []
        seen_values = set()
        for binlog in binlogs + last_binlogs:
            if binlog["backup_id"] not in seen_values:
                unique_list.append(self._serialize_backup_log(binlog))
                seen_values.add(binlog["backup_id"])

        return unique_list

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

        # 对每一份备份记录去重，相同的backup id不能出现重复的dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 对每个聚合记录补充信息
        backup_logs: List[Dict[str, Any]] = []
        for backup_id, logs in backup_id__valid_logs.items():
            start_time = min(map(str2datetime, [log["backup_begin_time"] for log in logs]))
            end_time = max(map(str2datetime, [log["backup_end_time"] for log in logs]))
            backup_log_info = {
                "start_time": datetime2str(start_time),
                "end_time": datetime2str(end_time),
                "backup_id": backup_id,
                "logs": logs,
                "complete": len(logs) == logs[0]["file_cnt"],
                "expected_cnt": logs[0]["file_cnt"],
                "real_cnt": len(logs),
                # 是否只取第一个log的角色就好了？
                "role": logs[0]["role"],
            }
            backup_logs.append(backup_log_info)
        backup_logs = sorted(backup_logs, key=lambda x: x["start_time"], reverse=True)
        return backup_logs

    def query_backup_logs_from_model(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        基于 SQLServerBackupResult Model 查询集群的备份记录（替代 bklog 查询）
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        backup_qs = SQLServerBackupResult.objects.filter(
            cluster_id=self.cluster.id,
            backup_end_time__gte=start_time,
            backup_end_time__lte=end_time,
        )
        backup_logs_raw = list(backup_qs.values())

        # 根据 backup_id 聚合备份记录，仅保留 data_schema_grant == "all" 的记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_logs_raw:
            if log["data_schema_grant"] == "all":
                backup_id__logs[log["backup_id"]].append(log)

        # 对每一份备份记录去重，相同的 backup_id 不能出现重复的 dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 对每个聚合记录补充信息
        result_logs: List[Dict[str, Any]] = []
        for backup_id, logs in backup_id__valid_logs.items():
            log_start_time = min(log["backup_begin_time"] for log in logs)
            log_end_time = max(log["backup_end_time"] for log in logs)
            # 计算已备份的 dbname 列表
            dbname_list = [log["dbname"] for log in logs]
            # 缺失的数据库 = db_list - 已备份的 dbname_list
            expected_db_list = logs[0]["db_list"]
            excluded_db_list = list(set(expected_db_list.split(",")) - set(dbname_list))

            # 将 logs 中的 datetime 字段转换为字符串，避免 JSON 序列化失败
            serialized_logs = [self._serialize_backup_log(log) for log in logs]

            backup_log_info = {
                "start_time": datetime2str(log_start_time),
                "end_time": datetime2str(log_end_time),
                "backup_id": backup_id,
                "logs": serialized_logs,
                "complete": len(logs) == logs[0]["file_cnt"],
                "expected_cnt": logs[0]["file_cnt"],
                "real_cnt": len(logs),
                "role": logs[0]["role"],  # 备份角色：logs 中其中的一个 role
                "backup_db_list": logs[0]["db_list"].split(","),  # 备份包含库：logs 中一个 db_list
                "backup_db_size_kb": sum(log["db_size_kb"] for log in logs),  # 数据库大小：同一个 backup_id 的 sum(db_size_kb)
                "backup_file_size_kb": sum(
                    log["file_size_kb"] for log in logs
                ),  # 备份文件大小：同一个 backup_id 的 sum(file_size_kb)
                "excluded_db_list": excluded_db_list,  # 排除库/缺失库：db_list - 已备份的 dbname_list
                "bill_id": logs[0]["bill_id"],  # 关联单据 id
            }
            result_logs.append(backup_log_info)

        result_logs = sorted(result_logs, key=lambda x: x["start_time"], reverse=True)
        return result_logs

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
            return {"logs": []}

        return backup_logs[latest_backup_log_index]

    def query_latest_backup_log_from_model(self, rollback_time: datetime):
        """
        基于 Model 查询，根据回档时间查询集群最近的备份记录
        @param rollback_time: 回档时间
        """
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = self.query_backup_logs_from_model(start_time, end_time)

        # 查询最近的备份记录
        backup_logs.sort(key=lambda x: x["end_time"])
        time_keys = [log["end_time"] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag=1)
        except IndexError:
            return {"logs": []}

        return backup_logs[latest_backup_log_index]

    def query_dbs_by_backup_log(
        self,
        db_pattern: List[str],
        ignore_db: List[str],
        backup_logs: List[Dict] = None,
        restore_time: datetime = None,
    ):
        """
        根据回档记录/回档时间，和库正则，过滤真正操作的DB库
        @param db_pattern: 库正则
        @param ignore_db: 忽略库正则
        @param backup_logs: 备份记录列表(这里只关注记录中的备份库字段)
        @param restore_time: 回档时间
        """
        if restore_time:
            backup_logs = self.query_latest_backup_log(restore_time)

        db_names = [log["dbname"] for log in backup_logs["logs"]]
        real_db_names = sqlserver_match_dbs(db_names, db_pattern, ignore_db)
        return real_db_names

    def query_last_log_time(self, query_time: datetime):
        """
        查询集群的最近一次上报的备份时间
        拿最新的一条备份记录的备份开始时间的作为判断依据
        """
        last_binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=query_time - timedelta(days=BACKUP_LOG_RANGE_DAYS),
            end_time=query_time,
            query_string=f"""cluster_id: {self.cluster.id} """,
            size=1,
            sort_rule="desc",
        )
        if not last_binlogs:
            raise Exception(_("集群【{}】最近的{}天里找不到日志备份").format(self.cluster.name, BACKUP_LOG_RANGE_DAYS))

        return last_binlogs[0]["backup_task_start_time"]

    def query_last_log_time_from_model(self, query_time: datetime):
        """
        基于 Model 查询集群的最近一次上报的备份时间
        拿最新的一条备份记录的备份开始时间的作为判断依据
        """
        last_binlog_qs = SQLServerBinlogResult.objects.filter(
            cluster_id=self.cluster.id,
            backup_task_start_time__gte=query_time - timedelta(days=BACKUP_LOG_RANGE_DAYS),
            backup_task_start_time__lte=query_time,
        ).order_by("-backup_task_start_time")[:1]

        last_binlogs = list(last_binlog_qs.values())
        if not last_binlogs:
            raise Exception(_("集群【{}】最近的{}天里找不到日志备份").format(self.cluster.name, BACKUP_LOG_RANGE_DAYS))

        return last_binlogs[0]["backup_task_start_time"]

    @staticmethod
    def check_binlog_lsn_continuity(backup_logs: List[Dict], full_backup_info: Dict) -> (List[Dict], List[str]):
        """
        检测一批量日志文件的连续性
        @param backup_logs: 日志备份列表
        @param full_backup_info: 关联的全量备份信息
        """
        check_lsn = 0
        check_file_name = ""
        err = []
        # 首先传入的list进行排序
        backup_logs.sort(key=lambda x: x["last_lsn"])
        # 对比每个日志备份的LSN的连续情况
        for log in backup_logs:
            if check_lsn == 0:
                # 表示是第一个lsn
                check_lsn = log["last_lsn"]
                check_file_name = log["file_name"]
                continue
            # 对比前一个last_lsn是否一致
            if check_lsn == log["first_lsn"]:
                check_lsn = log["last_lsn"]
                check_file_name = log["file_name"]
                continue
            # 不一致的话先记录日志，统一报错
            err.append(
                _(
                    "请联系系统管理员，恢复集群[{}]的数据库[{}]中拉取的日志备份存在不连续的情况:the first_lsn [{}]:[{}]; the last_lsn [{}]:[{}]\n"
                ).format(
                    full_backup_info["cluster_address"],
                    full_backup_info["db_name"],
                    check_file_name,
                    check_lsn,
                    log["file_name"],
                    log["first_lsn"],
                )
            )
        return backup_logs, err
